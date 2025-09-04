#!/usr/bin/env python3
"""
Fallback CD Script

Simulates CD pipeline locally when GitHub Actions are not available.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from deployment.releases import ReleaseManager
from deployment.rollouts import RolloutManager, RolloutStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deploy_to_staging(version: str, dry_run: bool = False):
    """Deploy to staging environment"""
    logger.info(f"🚀 Deploying version {version} to staging...")
    
    try:
        release_manager = ReleaseManager()
        
        # Create release if it doesn't exist
        release_result = release_manager.create_release(
            target="revops_suite",
            version=version,
            notes=f"Release candidate for staging deployment"
        )
        
        if not release_result['success']:
            logger.warning(f"Release creation warning: {release_result['error']}")
        
        # Promote to staging
        promote_result = release_manager.promote_release(
            target="revops_suite",
            version=version,
            environment="staging",
            dry_run=dry_run
        )
        
        if promote_result['success']:
            if dry_run:
                logger.info("✅ Staging promotion dry-run completed")
            else:
                logger.info("✅ Successfully promoted to staging")
                
                # Start rollout
                rollout_manager = RolloutManager()
                rollout_result = rollout_manager.start_rollout(
                    target="revops_suite",
                    version=version,
                    environment="staging",
                    strategy=RolloutStrategy.ROLLING,
                    dry_run=dry_run
                )
                
                if rollout_result['success']:
                    logger.info("✅ Staging rollout completed successfully")
                else:
                    logger.error(f"❌ Staging rollout failed: {rollout_result['error']}")
                    return False
        else:
            logger.error(f"❌ Staging promotion failed: {promote_result['error']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Staging deployment failed: {e}")
        return False

def deploy_to_production(version: str, strategy: str = "bluegreen", dry_run: bool = False):
    """Deploy to production environment"""
    logger.info(f"🚀 Deploying version {version} to production using {strategy}...")
    
    try:
        release_manager = ReleaseManager()
        
        # Verify staging deployment first
        staging_releases = release_manager.list_releases("revops_suite", "staged")
        if not any(r.version == version for r in staging_releases):
            logger.error(f"❌ Version {version} must be deployed to staging first")
            return False
        
        # Promote to production
        promote_result = release_manager.promote_release(
            target="revops_suite",
            version=version,
            environment="production",
            strategy=strategy,
            dry_run=dry_run
        )
        
        if promote_result['success']:
            if dry_run:
                logger.info("✅ Production promotion dry-run completed")
            else:
                logger.info("✅ Successfully promoted to production")
                
                # Start rollout
                rollout_manager = RolloutManager()
                rollout_strategy = RolloutStrategy.BLUE_GREEN if strategy == "bluegreen" else RolloutStrategy.ROLLING
                
                rollout_result = rollout_manager.start_rollout(
                    target="revops_suite",
                    version=version,
                    environment="production",
                    strategy=rollout_strategy,
                    dry_run=dry_run
                )
                
                if rollout_result['success']:
                    logger.info("✅ Production rollout completed successfully")
                else:
                    logger.error(f"❌ Production rollout failed: {rollout_result['error']}")
                    return False
        else:
            logger.error(f"❌ Production promotion failed: {promote_result['error']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Production deployment failed: {e}")
        return False

def rollback_production(target_version: str = None):
    """Rollback production deployment"""
    logger.info(f"🔄 Rolling back production deployment...")
    
    try:
        release_manager = ReleaseManager()
        
        rollback_result = release_manager.rollback_release(
            target="revops_suite",
            environment="production",
            to_version=target_version,
            dry_run=False
        )
        
        if rollback_result['success']:
            logger.info("✅ Production rollback completed successfully")
            return True
        else:
            logger.error(f"❌ Production rollback failed: {rollback_result['error']}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Production rollback failed: {e}")
        return False

def list_releases():
    """List all releases"""
    logger.info("📋 Listing releases...")
    
    try:
        release_manager = ReleaseManager()
        releases = release_manager.list_releases("revops_suite")
        
        if not releases:
            logger.info("No releases found")
            return
        
        for release in releases:
            logger.info(f"  📦 {release.name} v{release.version}")
            logger.info(f"     Status: {release.status}")
            logger.info(f"     Environment: {release.environment or 'N/A'}")
            logger.info(f"     Strategy: {release.strategy or 'N/A'}")
            logger.info(f"     Created: {release.created_at}")
            if release.promoted_at:
                logger.info(f"     Promoted: {release.promoted_at}")
            logger.info()
        
    except Exception as e:
        logger.error(f"❌ Failed to list releases: {e}")

def main():
    """Main CD execution"""
    parser = argparse.ArgumentParser(description="SBH CD Pipeline")
    parser.add_argument("action", choices=["staging", "production", "rollback", "list"], 
                       help="CD action to perform")
    parser.add_argument("--version", help="Version to deploy")
    parser.add_argument("--strategy", choices=["rolling", "bluegreen"], default="bluegreen",
                       help="Deployment strategy for production")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--to-version", help="Target version for rollback")
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    logger.info("🚀 Starting CD pipeline...")
    
    try:
        if args.action == "staging":
            if not args.version:
                logger.error("❌ Version is required for staging deployment")
                sys.exit(1)
            
            success = deploy_to_staging(args.version, args.dry_run)
            if not success:
                sys.exit(1)
                
        elif args.action == "production":
            if not args.version:
                logger.error("❌ Version is required for production deployment")
                sys.exit(1)
            
            success = deploy_to_production(args.version, args.strategy, args.dry_run)
            if not success:
                sys.exit(1)
                
        elif args.action == "rollback":
            success = rollback_production(args.to_version)
            if not success:
                sys.exit(1)
                
        elif args.action == "list":
            list_releases()
        
        logger.info("🎉 CD pipeline completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("⚠️  CD pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ CD pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
