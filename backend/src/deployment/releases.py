"""
Release & Versioning Core

Manages releases, versions, and deployment lifecycle for modules and ecosystems.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import re

try:
    from src.events import log_event
except ImportError:
    # Fallback for when running outside Flask context
    def log_event(event_type, tenant_id=None, module=None, payload=None):
        pass

logger = logging.getLogger(__name__)

@dataclass
class Release:
    """Release information for modules or ecosystems"""
    id: Optional[int]
    target: str  # module name or ecosystem name
    name: str
    version: str
    status: str  # draft, staged, prod, rolled_back
    artifacts: Dict[str, Any]
    changelog: str
    created_at: str
    promoted_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    environment: Optional[str] = None
    strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert release to dictionary"""
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate release configuration"""
        errors = []
        
        if not self.target:
            errors.append("Target is required")
        
        if not self.name:
            errors.append("Release name is required")
        
        if not self.version:
            errors.append("Version is required")
        elif not self._is_valid_semver(self.version):
            errors.append("Version must be valid semver (e.g., 1.0.0)")
        
        if self.status not in ['draft', 'staged', 'prod', 'rolled_back']:
            errors.append("Status must be one of: draft, staged, prod, rolled_back")
        
        return errors
    
    def _is_valid_semver(self, version: str) -> bool:
        """Check if version string is valid semver"""
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        return bool(re.match(pattern, version))

class ReleaseManager:
    """Manages releases and versioning for SBH"""
    
    def __init__(self, db_path: str = "system_builder_hub.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize releases table"""
        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS releases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target TEXT NOT NULL,
                        name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'draft',
                        artifacts TEXT NOT NULL,
                        changelog TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        promoted_at TIMESTAMP,
                        rolled_back_at TIMESTAMP,
                        environment TEXT,
                        strategy TEXT,
                        UNIQUE(target, version)
                    )
                """)
                conn.commit()
                logger.info("Releases table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize releases table: {e}")
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def create_release(self, target: str, version: str, notes: str = "", 
                      artifacts_meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new release"""
        try:
            # Generate release name
            release_name = f"{target}-{version}"
            
            # Default artifacts metadata
            if artifacts_meta is None:
                artifacts_meta = {
                    "type": "ecosystem" if target in ["revops_suite"] else "module",
                    "created_at": datetime.now().isoformat(),
                    "artifacts": []
                }
            
            # Create release object
            release = Release(
                id=None,
                target=target,
                name=release_name,
                version=version,
                status="draft",
                artifacts=artifacts_meta,
                changelog=notes,
                created_at=datetime.now().isoformat()
            )
            
            # Validate release
            errors = release.validate()
            if errors:
                return {
                    'success': False,
                    'error': f'Release validation failed: {errors}'
                }
            
            # Check if release already exists
            existing = self.get_release(target, version)
            if existing:
                return {
                    'success': False,
                    'error': f'Release {target} v{version} already exists'
                }
            
            # Store in database
            with self._get_db_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO releases (target, name, version, status, artifacts, changelog)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    release.target, release.name, release.version, release.status,
                    json.dumps(release.artifacts), release.changelog
                ))
                release.id = cursor.lastrowid
                conn.commit()
            
            # Log event
            log_event(
                'release_created',
                tenant_id='system',
                module='deployment',
                payload={
                    'target': target,
                    'version': version,
                    'release_name': release_name,
                    'status': 'draft'
                }
            )
            
            logger.info(f"Created release: {release_name}")
            
            return {
                'success': True,
                'data': release.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to create release: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_release(self, target: str, version: str) -> Optional[Release]:
        """Get a specific release by target and version"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM releases WHERE target = ? AND version = ?
                """, (target, version))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_release(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get release: {e}")
            return None
    
    def list_releases(self, target: str = None, status: str = None, 
                     limit: int = 50) -> List[Release]:
        """List releases with optional filtering"""
        try:
            with self._get_db_connection() as conn:
                query = "SELECT * FROM releases"
                params = []
                
                if target or status:
                    query += " WHERE"
                    if target:
                        query += " target = ?"
                        params.append(target)
                    if status:
                        if target:
                            query += " AND"
                        query += " status = ?"
                        params.append(status)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_release(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list releases: {e}")
            return []
    
    def promote_release(self, target: str, version: str, environment: str,
                       strategy: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """Promote a release to a specific environment"""
        try:
            # Get the release
            release = self.get_release(target, version)
            if not release:
                return {
                    'success': False,
                    'error': f'Release not found: {target} v{version}'
                }
            
            if release.status == 'rolled_back':
                return {
                    'success': False,
                    'error': f'Cannot promote rolled back release: {target} v{version}'
                }
            
            # Validate environment
            valid_envs = ['local', 'staging', 'production']
            if environment not in valid_envs:
                return {
                    'success': False,
                    'error': f'Invalid environment: {environment}. Must be one of {valid_envs}'
                }
            
            # Determine new status
            new_status = 'staged' if environment == 'staging' else 'prod'
            
            if dry_run:
                return {
                    'success': True,
                    'data': {
                        'action': 'promote',
                        'target': target,
                        'version': version,
                        'from_status': release.status,
                        'to_status': new_status,
                        'environment': environment,
                        'strategy': strategy,
                        'dry_run': True
                    }
                }
            
            # Update release status
            with self._get_db_connection() as conn:
                conn.execute("""
                    UPDATE releases SET 
                        status = ?, 
                        promoted_at = CURRENT_TIMESTAMP,
                        environment = ?,
                        strategy = ?
                    WHERE target = ? AND version = ?
                """, (new_status, environment, strategy, target, version))
                conn.commit()
            
            # Update local object
            release.status = new_status
            release.promoted_at = datetime.now().isoformat()
            release.environment = environment
            release.strategy = strategy
            
            # Log event
            log_event(
                'release_promoted',
                tenant_id='system',
                module='deployment',
                payload={
                    'target': target,
                    'version': version,
                    'from_status': 'draft',
                    'to_status': new_status,
                    'environment': environment,
                    'strategy': strategy
                }
            )
            
            logger.info(f"Promoted release {target} v{version} to {environment}")
            
            return {
                'success': True,
                'data': release.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to promote release: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def rollback_release(self, target: str, environment: str, 
                        to_version: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """Rollback a release in a specific environment"""
        try:
            # Get current production release
            current_release = None
            releases = self.list_releases(target, 'prod')
            if releases:
                current_release = releases[0]  # Most recent prod release
            
            if not current_release:
                return {
                    'success': False,
                    'error': f'No production release found for {target}'
                }
            
            # Determine target version for rollback
            if not to_version:
                # Find previous version
                all_releases = self.list_releases(target)
                prod_releases = [r for r in all_releases if r.status == 'prod']
                if len(prod_releases) < 2:
                    return {
                        'success': False,
                        'error': f'No previous version available for rollback'
                    }
                # Get second most recent prod release
                to_version = prod_releases[1].version
            
            # Get target release
            target_release = self.get_release(target, to_version)
            if not target_release:
                return {
                    'success': False,
                    'error': f'Target version not found: {target} v{to_version}'
                }
            
            if dry_run:
                return {
                    'success': True,
                    'data': {
                        'action': 'rollback',
                        'target': target,
                        'from_version': current_release.version,
                        'to_version': to_version,
                        'environment': environment,
                        'dry_run': True
                    }
                }
            
            # Mark current release as rolled back
            with self._get_db_connection() as conn:
                conn.execute("""
                    UPDATE releases SET 
                        status = 'rolled_back',
                        rolled_back_at = CURRENT_TIMESTAMP
                    WHERE target = ? AND version = ?
                """, (target, current_release.version))
                
                # Promote target version to production
                conn.execute("""
                    UPDATE releases SET 
                        status = 'prod',
                        promoted_at = CURRENT_TIMESTAMP,
                        environment = ?
                    WHERE target = ? AND version = ?
                """, (environment, target, to_version))
                
                conn.commit()
            
            # Log event
            log_event(
                'release_rolled_back',
                tenant_id='system',
                module='deployment',
                payload={
                    'target': target,
                    'from_version': current_release.version,
                    'to_version': to_version,
                    'environment': environment
                }
            )
            
            logger.info(f"Rolled back {target} from v{current_release.version} to v{to_version}")
            
            return {
                'success': True,
                'data': {
                    'action': 'rollback',
                    'target': target,
                    'from_version': current_release.version,
                    'to_version': to_version,
                    'environment': environment
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to rollback release: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _row_to_release(self, row) -> Release:
        """Convert database row to Release object"""
        try:
            artifacts = json.loads(row[5]) if row[5] else {}
        except:
            artifacts = {}
        
        return Release(
            id=row[0],
            target=row[1],
            name=row[2],
            version=row[3],
            status=row[4],
            artifacts=artifacts,
            changelog=row[6],
            created_at=row[7],
            promoted_at=row[8],
            rolled_back_at=row[9],
            environment=row[10],
            strategy=row[11]
        )
    
    def get_release_summary(self, target: str = None) -> Dict[str, Any]:
        """Get summary of releases for a target"""
        try:
            releases = self.list_releases(target)
            
            summary = {
                'total': len(releases),
                'by_status': {},
                'latest_by_env': {},
                'target': target
            }
            
            for release in releases:
                # Count by status
                status = release.status
                summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
                
                # Track latest by environment
                env = release.environment or 'unknown'
                if env not in summary['latest_by_env'] or release.created_at > summary['latest_by_env'][env].get('created_at', ''):
                    summary['latest_by_env'][env] = {
                        'version': release.version,
                        'created_at': release.created_at,
                        'status': release.status
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get release summary: {e}")
            return {}

def semver_bump(version: str, part: str) -> str:
    """Bump semver version by part (major, minor, patch)"""
    try:
        if part not in ['major', 'minor', 'patch']:
            raise ValueError("Part must be major, minor, or patch")
        
        parts = version.split('.')
        if len(parts) < 3:
            raise ValueError("Version must have at least 3 parts (major.minor.patch)")
        
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if part == 'major':
            major += 1
            minor = 0
            patch = 0
        elif part == 'minor':
            minor += 1
            patch = 0
        elif part == 'patch':
            patch += 1
        
        return f"{major}.{minor}.{patch}"
        
    except Exception as e:
        logger.error(f"Failed to bump version: {e}")
        return version

def validate_semver(version: str) -> bool:
    """Validate if a string is valid semver"""
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    return bool(re.match(pattern, version))
