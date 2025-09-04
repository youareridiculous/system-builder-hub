"""
Project Resumer for SBH Resume Mode

Auto-generates missing components to complete SBH integration for existing projects.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .project_analyzer import ProjectAnalyzer, ProjectAnalysis, ProjectArtifact
from .module_scaffolder import ModuleScaffolder
from .spec_parser import SpecParser

logger = logging.getLogger(__name__)

@dataclass
class ResumeAction:
    """Represents an action to complete a missing component"""
    component: str
    action: str
    description: str
    priority: str
    estimated_effort: str

class ProjectResumer:
    """Resumes incomplete projects by auto-generating missing SBH components"""
    
    def __init__(self, project_path: str, force: bool = False):
        self.project_path = Path(project_path).resolve()
        self.force = force
        self.analyzer = ProjectAnalyzer(str(project_path))
        self.scaffolder = ModuleScaffolder()
        self.spec_parser = SpecParser()
        self.changes_made = []
        
    def resume_project(self, dry_run: bool = False) -> Dict[str, Any]:
        """Resume a project by completing missing SBH components"""
        logger.info(f"Resuming project: {self.project_path}")
        
        # Analyze the project
        analysis = self.analyzer.analyze()
        
        if dry_run:
            return self._generate_dry_run_report(analysis)
        
        # Generate missing components
        results = {
            "project_path": str(self.project_path),
            "project_name": analysis.project_name,
            "compatibility_score_before": analysis.sbh_compatibility_score,
            "missing_components": analysis.missing_components,
            "changes_made": [],
            "errors": []
        }
        
        # Process missing components by priority
        missing_artifacts = [a for a in analysis.artifacts if a.status == "missing"]
        
        # Sort by priority (high -> medium -> low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        missing_artifacts.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        for artifact in missing_artifacts:
            try:
                change = self._generate_missing_component(artifact)
                if change:
                    results["changes_made"].append(change)
                    self.changes_made.append(change)
            except Exception as e:
                error_msg = f"Failed to generate {artifact.name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Re-analyze to get updated compatibility score
        updated_analysis = self.analyzer.analyze()
        results["compatibility_score_after"] = updated_analysis.sbh_compatibility_score
        
        # Generate final report
        self._generate_resume_report(results, analysis, updated_analysis)
        
        return results
    
    def _generate_dry_run_report(self, analysis: ProjectAnalysis) -> Dict[str, Any]:
        """Generate a dry-run report showing what would be done"""
        missing_artifacts = [a for a in analysis.artifacts if a.status == "missing"]
        
        actions = []
        for artifact in missing_artifacts:
            action = self._get_resume_action(artifact)
            actions.append(action)
        
        return {
            "project_path": str(self.project_path),
            "project_name": analysis.project_name,
            "compatibility_score": analysis.sbh_compatibility_score,
            "missing_components": analysis.missing_components,
            "proposed_actions": actions,
            "dry_run": True
        }
    
    def _get_resume_action(self, artifact: ProjectArtifact) -> ResumeAction:
        """Get the resume action for a missing artifact"""
        if artifact.name == "Database Migrations":
            return ResumeAction(
                component=artifact.name,
                action="Generate Alembic migration",
                description="Create database schema migration files",
                priority=artifact.priority,
                estimated_effort="5-10 minutes"
            )
        elif artifact.name == "API Blueprints":
            return ResumeAction(
                component=artifact.name,
                action="Generate Flask API blueprints",
                description="Create REST API endpoints",
                priority=artifact.priority,
                estimated_effort="10-15 minutes"
            )
        elif artifact.name == "CLI Commands":
            return ResumeAction(
                component=artifact.name,
                action="Generate CLI commands",
                description="Create command-line interface",
                priority=artifact.priority,
                estimated_effort="5-10 minutes"
            )
        elif artifact.name == "Marketplace Entry":
            return ResumeAction(
                component=artifact.name,
                action="Generate marketplace JSON",
                description="Create marketplace configuration",
                priority=artifact.priority,
                estimated_effort="5 minutes"
            )
        elif artifact.name == "Onboarding Documentation":
            return ResumeAction(
                component=artifact.name,
                action="Generate onboarding docs",
                description="Create setup and usage documentation",
                priority=artifact.priority,
                estimated_effort="10 minutes"
            )
        elif artifact.name == "Test Files":
            return ResumeAction(
                component=artifact.name,
                action="Generate test files",
                description="Create unit and integration tests",
                priority=artifact.priority,
                estimated_effort="15-20 minutes"
            )
        elif artifact.name == "Data Models":
            return ResumeAction(
                component=artifact.name,
                action="Generate data models",
                description="Create SQLAlchemy models",
                priority=artifact.priority,
                estimated_effort="10-15 minutes"
            )
        elif artifact.name == "Seed Data":
            return ResumeAction(
                component=artifact.name,
                action="Generate seed data",
                description="Create demo data seeding",
                priority=artifact.priority,
                estimated_effort="5-10 minutes"
            )
        else:
            return ResumeAction(
                component=artifact.name,
                action="Generate component",
                description=f"Create {artifact.name.lower()}",
                priority=artifact.priority,
                estimated_effort="5-10 minutes"
            )
    
    def _generate_missing_component(self, artifact: ProjectArtifact) -> Optional[Dict[str, Any]]:
        """Generate a missing component based on the artifact"""
        logger.info(f"Generating missing component: {artifact.name}")
        
        # Check if we should overwrite existing files
        if artifact.path.exists() and not self.force:
            logger.warning(f"Skipping {artifact.name} - file exists and --force not specified")
            return None
        
        try:
            if artifact.name == "Database Migrations":
                return self._generate_migrations()
            elif artifact.name == "API Blueprints":
                return self._generate_api_blueprints()
            elif artifact.name == "CLI Commands":
                return self._generate_cli_commands()
            elif artifact.name == "Marketplace Entry":
                return self._generate_marketplace_entry()
            elif artifact.name == "Onboarding Documentation":
                return self._generate_onboarding_docs()
            elif artifact.name == "Test Files":
                return self._generate_test_files()
            elif artifact.name == "Data Models":
                return self._generate_data_models()
            elif artifact.name == "Seed Data":
                return self._generate_seed_data()
            else:
                logger.warning(f"Unknown artifact type: {artifact.name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate {artifact.name}: {e}")
            raise
    
    def _generate_migrations(self) -> Dict[str, Any]:
        """Generate database migrations"""
        # Create migrations directory
        migrations_dir = self.project_path / "migrations"
        migrations_dir.mkdir(exist_ok=True)
        
        # Create a basic migration file
        migration_content = '''"""Initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2025-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial tables"""
    # Add your table creation logic here
    pass

def downgrade():
    """Drop initial tables"""
    # Add your table dropping logic here
    pass
'''
        
        migration_file = migrations_dir / "001_initial_migration.py"
        with open(migration_file, 'w') as f:
            f.write(migration_content)
        
        return {
            "component": "Database Migrations",
            "action": "Created initial migration",
            "file": str(migration_file),
            "status": "success"
        }
    
    def _generate_api_blueprints(self) -> Dict[str, Any]:
        """Generate API blueprints"""
        # Create API directory
        api_dir = self.project_path / "src" / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py
        init_file = api_dir / "__init__.py"
        init_file.touch()
        
        # Create basic API blueprint
        api_content = '''"""Basic API blueprint for SBH integration"""

from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "api"
    })

@api_bp.route('/status', methods=['GET'])
def status():
    """Status endpoint"""
    return jsonify({
        "status": "running",
        "version": "1.0.0"
    })
'''
        
        api_file = api_dir / "main_api.py"
        with open(api_file, 'w') as f:
            f.write(api_content)
        
        return {
            "component": "API Blueprints",
            "action": "Created basic API blueprint",
            "file": str(api_file),
            "status": "success"
        }
    
    def _generate_cli_commands(self) -> Dict[str, Any]:
        """Generate CLI commands"""
        cli_file = self.project_path / "src" / "cli.py"
        
        cli_content = '''"""CLI commands for SBH integration"""

import click
import logging

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """CLI commands for the project"""
    pass

@cli.command()
def status():
    """Check project status"""
    click.echo("✅ Project is running")
    click.echo("🔧 SBH integration in progress")

@cli.command()
def seed():
    """Seed demo data"""
    click.echo("🌱 Seeding demo data...")
    # Add your seeding logic here
    click.echo("✅ Demo data seeded successfully")

@cli.command()
def reset():
    """Reset project data"""
    click.echo("🔄 Resetting project data...")
    # Add your reset logic here
    click.echo("✅ Project data reset successfully")

if __name__ == '__main__':
    cli()
'''
        
        with open(cli_file, 'w') as f:
            f.write(cli_content)
        
        return {
            "component": "CLI Commands",
            "action": "Created CLI commands",
            "file": str(cli_file),
            "status": "success"
        }
    
    def _generate_marketplace_entry(self) -> Dict[str, Any]:
        """Generate marketplace entry"""
        marketplace_dir = self.project_path / "marketplace"
        marketplace_dir.mkdir(exist_ok=True)
        
        # Try to infer project details
        project_name = self.project_path.name.replace('-', ' ').replace('_', ' ').title()
        
        marketplace_content = {
            "slug": self.project_path.name,
            "name": project_name,
            "description": f"Auto-generated {project_name} module for SBH integration",
            "category": "Business",
            "tags": [self.project_path.name, "sbh-integrated"],
            "version": "1.0.0",
            "author": "SBH Auto-Generator",
            "features": [
                "Basic functionality",
                "SBH integration",
                "API endpoints",
                "CLI commands"
            ],
            "plans": {
                "starter": {
                    "name": "Starter",
                    "price": 0,
                    "billing_cycle": "monthly",
                    "features": [
                        "Basic functionality"
                    ]
                },
                "pro": {
                    "name": "Pro",
                    "price": 99,
                    "billing_cycle": "monthly",
                    "features": [
                        "Advanced features",
                        "Priority support"
                    ]
                }
            },
            "is_active": True,
            "created_at": "2025-09-01T00:00:00.000000Z",
            "updated_at": "2025-09-01T00:00:00.000000Z"
        }
        
        marketplace_file = marketplace_dir / f"{self.project_path.name}.json"
        with open(marketplace_file, 'w') as f:
            json.dump(marketplace_content, f, indent=2)
        
        return {
            "component": "Marketplace Entry",
            "action": "Created marketplace JSON",
            "file": str(marketplace_file),
            "status": "success"
        }
    
    def _generate_onboarding_docs(self) -> Dict[str, Any]:
        """Generate onboarding documentation"""
        readme_content = f'''# {self.project_path.name.title()}

## Overview

This project has been integrated with System Builder Hub (SBH) for enhanced functionality and deployment capabilities.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python -m src.cli run
   ```

3. **Check status:**
   ```bash
   python -m src.cli status
   ```

## SBH Integration

This project has been automatically integrated with SBH and includes:

- ✅ Database migrations
- ✅ API blueprints
- ✅ CLI commands
- ✅ Marketplace entry
- ✅ Onboarding documentation

## Development

### Adding new features

1. Create your models in `src/models.py`
2. Add API endpoints in `src/api/`
3. Create CLI commands in `src/cli.py`
4. Update marketplace configuration in `marketplace/`

### Testing

```bash
python -m pytest tests/
```

## Deployment

This project is ready for deployment through SBH's marketplace system.

## Support

For support, please refer to the SBH documentation or contact the development team.
'''
        
        readme_file = self.project_path / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        return {
            "component": "Onboarding Documentation",
            "action": "Created README.md",
            "file": str(readme_file),
            "status": "success"
        }
    
    def _generate_test_files(self) -> Dict[str, Any]:
        """Generate test files"""
        tests_dir = self.project_path / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        init_file = tests_dir / "__init__.py"
        init_file.touch()
        
        # Create basic test file
        test_content = '''"""Basic tests for SBH integration"""

import pytest
from pathlib import Path

def test_project_structure():
    """Test that project has basic SBH structure"""
    project_root = Path(__file__).parent.parent
    
    # Check for essential directories
    assert (project_root / "src").exists(), "src/ directory missing"
    assert (project_root / "marketplace").exists(), "marketplace/ directory missing"
    
    # Check for essential files
    assert (project_root / "src" / "cli.py").exists(), "CLI file missing"
    assert (project_root / "README.md").exists(), "README.md missing"

def test_api_structure():
    """Test that API structure is in place"""
    project_root = Path(__file__).parent.parent
    api_dir = project_root / "src" / "api"
    
    if api_dir.exists():
        api_files = list(api_dir.glob("*.py"))
        assert len(api_files) > 0, "No API files found"

def test_marketplace_entry():
    """Test that marketplace entry exists"""
    project_root = Path(__file__).parent.parent
    marketplace_dir = project_root / "marketplace"
    
    if marketplace_dir.exists():
        json_files = list(marketplace_dir.glob("*.json"))
        assert len(json_files) > 0, "No marketplace JSON files found"
'''
        
        test_file = tests_dir / "test_sbh_integration.py"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        return {
            "component": "Test Files",
            "action": "Created basic tests",
            "file": str(test_file),
            "status": "success"
        }
    
    def _generate_data_models(self) -> Dict[str, Any]:
        """Generate data models"""
        models_file = self.project_path / "src" / "models.py"
        
        models_content = '''"""Data models for SBH integration"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Project(Base):
    """Basic project model"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Project(name='{self.name}')>"

class User(Base):
    """Basic user model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}')>"
'''
        
        with open(models_file, 'w') as f:
            f.write(models_content)
        
        return {
            "component": "Data Models",
            "action": "Created basic models",
            "file": str(models_file),
            "status": "success"
        }
    
    def _generate_seed_data(self) -> Dict[str, Any]:
        """Generate seed data"""
        seed_file = self.project_path / "src" / "seed.py"
        
        seed_content = '''"""Seed data for SBH integration"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Project, User

logger = logging.getLogger(__name__)

def seed_demo_data():
    """Seed demo data for the project"""
    logger.info("Seeding demo data...")
    
    # Create engine and session
    engine = create_engine('sqlite:///project.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create demo projects
        projects = [
            Project(name="Demo Project 1", description="First demo project"),
            Project(name="Demo Project 2", description="Second demo project"),
        ]
        
        for project in projects:
            session.add(project)
        
        # Create demo users
        users = [
            User(username="demo_user1", email="user1@demo.com"),
            User(username="demo_user2", email="user2@demo.com"),
        ]
        
        for user in users:
            session.add(user)
        
        session.commit()
        logger.info("Demo data seeded successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_demo_data()
'''
        
        with open(seed_file, 'w') as f:
            f.write(seed_content)
        
        return {
            "component": "Seed Data",
            "action": "Created seed data",
            "file": str(seed_file),
            "status": "success"
        }
    
    def _generate_resume_report(self, results: Dict[str, Any], 
                               before_analysis: ProjectAnalysis, 
                               after_analysis: ProjectAnalysis):
        """Generate a resume completion report"""
        report_file = self.project_path / "resume.completion.md"
        
        report_lines = [
            "# SBH Project Resume Completion Report",
            "",
            f"**Project:** {results['project_name']}",
            f"**Path:** {results['project_path']}",
            f"**Resume Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Compatibility Score",
            f"- **Before:** {results['compatibility_score_before']:.1%}",
            f"- **After:** {results['compatibility_score_after']:.1%}",
            f"- **Improvement:** {results['compatibility_score_after'] - results['compatibility_score_before']:.1%}",
            "",
            "## Changes Made",
            ""
        ]
        
        if results['changes_made']:
            for change in results['changes_made']:
                report_lines.append(f"- **{change['component']}**: {change['action']}")
                report_lines.append(f"  - File: `{change['file']}`")
                report_lines.append(f"  - Status: {change['status']}")
                report_lines.append("")
        else:
            report_lines.append("- No changes were made (all components already present)")
            report_lines.append("")
        
        if results['errors']:
            report_lines.extend([
                "## Errors",
                ""
            ])
            for error in results['errors']:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        report_lines.extend([
            "## Next Steps",
            "",
            "Your project is now SBH-integrated! You can:",
            "",
            "1. **Test the integration:**",
            "   ```bash",
            "   python -m src.cli status",
            "   ```",
            "",
            "2. **Run the application:**",
            "   ```bash",
            "   python -m src.cli run",
            "   ```",
            "",
            "3. **Seed demo data:**",
            "   ```bash",
            "   python -m src.cli seed",
            "   ```",
            "",
            "4. **Deploy to SBH marketplace:**",
            "   ```bash",
            "   python -m src.cli marketplace deploy",
            "   ```"
        ])
        
        report_content = "\n".join(report_lines)
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Resume completion report saved to: {report_file}")
