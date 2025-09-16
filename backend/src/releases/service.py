"""
Release management service
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.releases.models import Environment, Release, ReleaseMigration, FeatureFlag
from src.database import db_session
from src.analytics.service import AnalyticsService
from src.agent_tools.kernel import tool_kernel
from src.agent_tools.types import ToolCall, ToolContext

logger = logging.getLogger(__name__)

class ReleaseService:
    """Release management service"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
    
    def prepare_release(self, tenant_id: str, from_env: str, to_env: str, 
                       bundle_data: Dict[str, Any], user_id: str) -> Release:
        """Prepare a release from one environment to another"""
        try:
            # Generate release ID
            release_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            # Calculate bundle checksum
            bundle_sha256 = hashlib.sha256(
                json.dumps(bundle_data, sort_keys=True).encode()
            ).hexdigest()
            
            # Generate migration plan using db.migrate tool
            migrations = self._generate_migration_plan(tenant_id, bundle_data)
            
            # Create release record
            release = Release(
                release_id=release_id,
                tenant_id=tenant_id,
                from_env=from_env,
                to_env=to_env,
                bundle_sha256=bundle_sha256,
                migrations=migrations,
                feature_flags=self._get_feature_flags(tenant_id),
                tools_transcript_ids=[],  # Will be populated during tool calls
                status='prepared',
                created_by=user_id
            )
            
            with db_session() as session:
                session.add(release)
                session.commit()
                session.refresh(release)
            
            # Track analytics
            self.analytics.track(
                tenant_id=tenant_id,
                event='release.prepared',
                user_id=user_id,
                source='releases',
                props={
                    'release_id': release_id,
                    'from_env': from_env,
                    'to_env': to_env,
                    'migrations_count': len(migrations)
                }
            )
            
            logger.info(f"Release prepared: {release_id} ({from_env} → {to_env})")
            return release
            
        except Exception as e:
            logger.error(f"Error preparing release: {e}")
            raise
    
    def promote_release(self, release_id: str, user_id: str) -> Release:
        """Promote a release to the target environment"""
        try:
            with db_session() as session:
                release = session.query(Release).filter(
                    Release.release_id == release_id
                ).first()
                
                if not release:
                    raise ValueError(f"Release not found: {release_id}")
                
                if release.status != 'prepared':
                    raise ValueError(f"Release {release_id} is not in prepared status")
                
                # Apply migrations
                success = self._apply_migrations(release, user_id)
                
                if success:
                    release.status = 'promoted'
                    release.promoted_at = datetime.utcnow()
                    
                    # Track success
                    self.analytics.track(
                        tenant_id=release.tenant_id,
                        event='release.promoted',
                        user_id=user_id,
                        source='releases',
                        props={
                            'release_id': release_id,
                            'from_env': release.from_env,
                            'to_env': release.to_env
                        }
                    )
                    
                    logger.info(f"Release promoted: {release_id}")
                else:
                    release.status = 'failed'
                    release.failed_at = datetime.utcnow()
                    release.error_message = "Migration application failed"
                    
                    # Track failure
                    self.analytics.track(
                        tenant_id=release.tenant_id,
                        event='release.failed',
                        user_id=user_id,
                        source='releases',
                        props={
                            'release_id': release_id,
                            'from_env': release.from_env,
                            'to_env': release.to_env,
                            'error': 'Migration application failed'
                        }
                    )
                    
                    logger.error(f"Release failed: {release_id}")
                
                session.commit()
                session.refresh(release)
                return release
                
        except Exception as e:
            logger.error(f"Error promoting release: {e}")
            raise
    
    def rollback_release(self, release_id: str, user_id: str) -> bool:
        """Rollback a release"""
        try:
            with db_session() as session:
                release = session.query(Release).filter(
                    Release.release_id == release_id
                ).first()
                
                if not release:
                    raise ValueError(f"Release not found: {release_id}")
                
                # Find previous successful release
                prev_release = session.query(Release).filter(
                    Release.tenant_id == release.tenant_id,
                    Release.to_env == release.to_env,
                    Release.status == 'promoted',
                    Release.id != release.id
                ).order_by(Release.promoted_at.desc()).first()
                
                if not prev_release:
                    logger.warning(f"No previous release found for rollback: {release_id}")
                    return False
                
                # Apply rollback migrations
                success = self._apply_rollback_migrations(release, prev_release, user_id)
                
                if success:
                    release.status = 'rolled_back'
                    
                    # Track rollback
                    self.analytics.track(
                        tenant_id=release.tenant_id,
                        event='release.rollback',
                        user_id=user_id,
                        source='releases',
                        props={
                            'release_id': release_id,
                            'rollback_to': prev_release.release_id
                        }
                    )
                    
                    logger.info(f"Release rolled back: {release_id}")
                    return True
                else:
                    logger.error(f"Rollback failed: {release_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error rolling back release: {e}")
            return False
    
    def _generate_migration_plan(self, tenant_id: str, bundle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate migration plan using db.migrate tool"""
        migrations = []
        
        try:
            # Create tool context
            tool_context = ToolContext(
                tenant_id=tenant_id,
                user_id='system',
                role='admin'
            )
            
            # Extract database changes from bundle
            db_changes = bundle_data.get('database', {}).get('changes', [])
            
            for change in db_changes:
                if change['type'] == 'create_table':
                    # Create table migration
                    call = ToolCall(
                        id=f"mig_{len(migrations)}",
                        tool='db.migrate',
                        args={
                            'op': 'create_table',
                            'table': change['table'],
                            'columns': change['columns'],
                            'dry_run': True
                        }
                    )
                    
                    result = tool_kernel.execute(call, tool_context)
                    if result.ok:
                        migrations.append({
                            'operation': 'create_table',
                            'table': change['table'],
                            'sql': result.redacted_output.get('sql', ''),
                            'dry_run_result': result.redacted_output
                        })
                
                elif change['type'] == 'add_column':
                    # Add column migration
                    call = ToolCall(
                        id=f"mig_{len(migrations)}",
                        tool='db.migrate',
                        args={
                            'op': 'add_column',
                            'table': change['table'],
                            'column': change['column'],
                            'dry_run': True
                        }
                    )
                    
                    result = tool_kernel.execute(call, tool_context)
                    if result.ok:
                        migrations.append({
                            'operation': 'add_column',
                            'table': change['table'],
                            'sql': result.redacted_output.get('sql', ''),
                            'dry_run_result': result.redacted_output
                        })
            
        except Exception as e:
            logger.error(f"Error generating migration plan: {e}")
        
        return migrations
    
    def _apply_migrations(self, release: Release, user_id: str) -> bool:
        """Apply migrations for a release"""
        try:
            # Create tool context
            tool_context = ToolContext(
                tenant_id=release.tenant_id,
                user_id=user_id,
                role='admin'
            )
            
            success_count = 0
            
            for migration in release.migrations:
                try:
                    # Apply migration
                    call = ToolCall(
                        id=f"apply_{migration['operation']}_{migration['table']}",
                        tool='db.migrate',
                        args={
                            'op': migration['operation'],
                            'table': migration['table'],
                            'sql': migration['sql']
                        }
                    )
                    
                    result = tool_kernel.execute(call, tool_context)
                    if result.ok:
                        success_count += 1
                        logger.info(f"Migration applied: {migration['operation']} on {migration['table']}")
                    else:
                        logger.error(f"Migration failed: {migration['operation']} on {migration['table']}: {result.error}")
                        return False
                
                except Exception as e:
                    logger.error(f"Error applying migration: {e}")
                    return False
            
            return success_count == len(release.migrations)
            
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def _apply_rollback_migrations(self, release: Release, prev_release: Release, user_id: str) -> bool:
        """Apply rollback migrations"""
        try:
            # Create tool context
            tool_context = ToolContext(
                tenant_id=release.tenant_id,
                user_id=user_id,
                role='admin'
            )
            
            # For now, we'll implement a simple rollback strategy
            # In a real implementation, this would be more sophisticated
            
            # Track rollback attempt
            self.analytics.track(
                tenant_id=release.tenant_id,
                event='release.rollback.attempted',
                user_id=user_id,
                source='releases',
                props={
                    'release_id': release.release_id,
                    'rollback_to': prev_release.release_id
                }
            )
            
            logger.info(f"Rollback attempted: {release.release_id} → {prev_release.release_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying rollback migrations: {e}")
            return False
    
    def _get_feature_flags(self, tenant_id: str) -> Dict[str, Any]:
        """Get feature flags for tenant"""
        try:
            with db_session() as session:
                flags = session.query(FeatureFlag).filter(
                    FeatureFlag.tenant_id == tenant_id
                ).all()
                
                return {
                    flag.name: flag.value for flag in flags
                }
        except Exception as e:
            logger.error(f"Error getting feature flags: {e}")
            return {}
    
    def get_releases(self, tenant_id: str, limit: int = 50) -> List[Release]:
        """Get releases for tenant"""
        try:
            with db_session() as session:
                releases = session.query(Release).filter(
                    Release.tenant_id == tenant_id
                ).order_by(Release.created_at.desc()).limit(limit).all()
                
                return releases
        except Exception as e:
            logger.error(f"Error getting releases: {e}")
            return []
    
    def get_release(self, release_id: str) -> Optional[Release]:
        """Get a specific release"""
        try:
            with db_session() as session:
                release = session.query(Release).filter(
                    Release.release_id == release_id
                ).first()
                
                return release
        except Exception as e:
            logger.error(f"Error getting release: {e}")
            return None
