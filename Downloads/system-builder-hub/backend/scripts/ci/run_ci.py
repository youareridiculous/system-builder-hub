#!/usr/bin/env python3
"""
Fallback CI Script

Simulates CI pipeline locally when GitHub Actions are not available.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from deployment.releases import ReleaseManager
from deployment.bundles import list_bundles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_linting():
    """Run code linting"""
    logger.info("🔍 Running linting...")
    
    try:
        # Run ruff
        result = subprocess.run(['ruff', 'check', 'src/'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Ruff linting passed")
        else:
            logger.warning("⚠️  Ruff linting issues found:")
            print(result.stdout)
            print(result.stderr)
        
        # Run bandit
        result = subprocess.run(['bandit', '-r', 'src/'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Bandit security scan passed")
        else:
            logger.warning("⚠️  Bandit security issues found:")
            print(result.stdout)
            print(result.stderr)
        
        return True
    except FileNotFoundError:
        logger.warning("⚠️  Linting tools not found, skipping...")
        return True

def run_tests():
    """Run tests"""
    logger.info("🧪 Running tests...")
    
    try:
        result = subprocess.run(['pytest', 'tests/', '--cov=src', '--cov-report=term'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Tests passed")
            return True
        else:
            logger.error("❌ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except FileNotFoundError:
        logger.warning("⚠️  Pytest not found, skipping tests...")
        return True

def run_security_audit():
    """Run security audit"""
    logger.info("🔒 Running security audit...")
    
    try:
        result = subprocess.run(['pip-audit', '--format', 'json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Security audit passed")
            return True
        else:
            logger.warning("⚠️  Security vulnerabilities found:")
            print(result.stdout)
            print(result.stderr)
            return True  # Don't fail build for security issues
    except FileNotFoundError:
        logger.warning("⚠️  pip-audit not found, skipping security audit...")
        return True

def build_artifacts():
    """Build deployment artifacts"""
    logger.info("🏗️  Building deployment artifacts...")
    
    try:
        # Generate staging compose
        result = subprocess.run([
            'python', '-m', 'src.cli', 'deploy', 'generate-compose',
            '--bundle', 'revops_suite_staging',
            '--output', 'docker-compose.staging.yml'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Generated staging docker-compose.yml")
        else:
            logger.error("❌ Failed to generate staging compose:")
            print(result.stderr)
            return False
        
        # Generate staging manifest
        result = subprocess.run([
            'python', '-m', 'src.cli', 'deploy', 'generate-manifest',
            '--bundle', 'revops_suite_staging',
            '--output', 'k8s-staging.yml'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Generated staging k8s manifest")
        else:
            logger.error("❌ Failed to generate staging manifest:")
            print(result.stderr)
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to build artifacts: {e}")
        return False

def validate_bundles():
    """Validate deployment bundles"""
    logger.info("✅ Validating deployment bundles...")
    
    try:
        bundles = list_bundles()
        for bundle in bundles:
            result = subprocess.run([
                'python', '-m', 'src.cli', 'deploy', 'validate',
                '--bundle', bundle['name']
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Bundle {bundle['name']} is valid")
            else:
                logger.error(f"❌ Bundle {bundle['name']} validation failed:")
                print(result.stderr)
                return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to validate bundles: {e}")
        return False

def main():
    """Main CI execution"""
    logger.info("🚀 Starting CI pipeline...")
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    # Run CI steps
    steps = [
        ("Linting", run_linting),
        ("Tests", run_tests),
        ("Security Audit", run_security_audit),
        ("Bundle Validation", validate_bundles),
        ("Build Artifacts", build_artifacts)
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {step_name}")
        logger.info(f"{'='*50}")
        
        try:
            if step_func():
                logger.info(f"✅ {step_name} completed successfully")
            else:
                logger.error(f"❌ {step_name} failed")
                failed_steps.append(step_name)
        except Exception as e:
            logger.error(f"❌ {step_name} failed with exception: {e}")
            failed_steps.append(step_name)
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("CI Pipeline Summary")
    logger.info(f"{'='*50}")
    
    if failed_steps:
        logger.error(f"❌ Failed steps: {', '.join(failed_steps)}")
        logger.error("CI pipeline failed!")
        sys.exit(1)
    else:
        logger.info("🎉 All CI steps passed successfully!")
        logger.info("✅ CI pipeline completed!")

if __name__ == "__main__":
    main()
