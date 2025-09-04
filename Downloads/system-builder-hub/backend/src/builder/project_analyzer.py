"""
Project Analyzer for SBH Resume Mode

Analyzes existing codebases to detect SBH-compatible artifacts and identify gaps
that need to be filled to make the project fully SBH-integrated.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ProjectArtifact:
    """Represents a detected SBH artifact in the project"""
    name: str
    path: Path
    status: str  # "present", "missing", "incomplete"
    description: str
    priority: str = "medium"  # "high", "medium", "low"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProjectAnalysis:
    """Complete analysis of a project's SBH compatibility"""
    project_path: Path
    project_name: str
    artifacts: List[ProjectArtifact] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    sbh_compatibility_score: float = 0.0

class ProjectAnalyzer:
    """Analyzes projects for SBH compatibility and identifies gaps"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.analysis = ProjectAnalysis(
            project_path=self.project_path,
            project_name=self.project_path.name
        )
        
    def analyze(self) -> ProjectAnalysis:
        """Perform complete project analysis"""
        logger.info(f"Analyzing project: {self.project_path}")
        
        # Detect project structure
        self._detect_project_structure()
        
        # Analyze SBH-specific artifacts
        self._analyze_migrations()
        self._analyze_api_blueprints()
        self._analyze_cli_commands()
        self._analyze_marketplace_entry()
        self._analyze_onboarding_docs()
        self._analyze_tests()
        self._analyze_models()
        self._analyze_seed_data()
        
        # Calculate compatibility score
        self._calculate_compatibility_score()
        
        # Generate recommendations
        self._generate_recommendations()
        
        return self.analysis
    
    def _detect_project_structure(self):
        """Detect basic project structure"""
        logger.info("Detecting project structure...")
        
        # Check if it's a Python project
        if (self.project_path / "requirements.txt").exists():
            self.analysis.artifacts.append(ProjectArtifact(
                name="Python Project",
                path=self.project_path / "requirements.txt",
                status="present",
                description="Python project with requirements.txt",
                priority="high"
            ))
        
        # Check for src directory
        src_path = self.project_path / "src"
        if src_path.exists() and src_path.is_dir():
            self.analysis.artifacts.append(ProjectArtifact(
                name="Source Directory",
                path=src_path,
                status="present",
                description="Standard src/ directory structure",
                priority="high"
            ))
        else:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Source Directory",
                path=src_path,
                status="missing",
                description="Missing src/ directory for SBH structure",
                priority="high"
            ))
    
    def _analyze_migrations(self):
        """Analyze database migrations"""
        logger.info("Analyzing database migrations...")
        
        # Look for common migration directories
        migration_paths = [
            self.project_path / "migrations",
            self.project_path / "alembic",
            self.project_path / "src" / "migrations",
            self.project_path / "db" / "migrations"
        ]
        
        migration_found = False
        for migration_path in migration_paths:
            if migration_path.exists():
                migration_files = list(migration_path.rglob("*.py"))
                if migration_files:
                    self.analysis.artifacts.append(ProjectArtifact(
                        name="Database Migrations",
                        path=migration_path,
                        status="present",
                        description=f"Found {len(migration_files)} migration files",
                        priority="high",
                        details={"migration_count": len(migration_files)}
                    ))
                    migration_found = True
                    break
        
        if not migration_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Database Migrations",
                path=self.project_path / "migrations",
                status="missing",
                description="No database migrations found",
                priority="high"
            ))
    
    def _analyze_api_blueprints(self):
        """Analyze Flask API blueprints"""
        logger.info("Analyzing API blueprints...")
        
        # Look for API files in common locations
        api_paths = [
            self.project_path / "src" / "api",
            self.project_path / "api",
            self.project_path / "src" / "routes",
            self.project_path / "routes"
        ]
        
        api_found = False
        for api_path in api_paths:
            if api_path.exists():
                api_files = list(api_path.rglob("*.py"))
                if api_files:
                    self.analysis.artifacts.append(ProjectArtifact(
                        name="API Blueprints",
                        path=api_path,
                        status="present",
                        description=f"Found {len(api_files)} API files",
                        priority="high",
                        details={"api_file_count": len(api_files)}
                    ))
                    api_found = True
                    break
        
        if not api_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="API Blueprints",
                path=self.project_path / "src" / "api",
                status="missing",
                description="No API blueprints found",
                priority="high"
            ))
    
    def _analyze_cli_commands(self):
        """Analyze CLI commands"""
        logger.info("Analyzing CLI commands...")
        
        # Look for CLI files
        cli_paths = [
            self.project_path / "src" / "cli.py",
            self.project_path / "cli.py",
            self.project_path / "src" / "commands.py"
        ]
        
        cli_found = False
        for cli_path in cli_paths:
            if cli_path.exists():
                self.analysis.artifacts.append(ProjectArtifact(
                    name="CLI Commands",
                    path=cli_path,
                    status="present",
                    description="CLI commands file found",
                    priority="medium"
                ))
                cli_found = True
                break
        
        if not cli_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="CLI Commands",
                path=self.project_path / "src" / "cli.py",
                status="missing",
                description="No CLI commands found",
                priority="medium"
            ))
    
    def _analyze_marketplace_entry(self):
        """Analyze marketplace entry"""
        logger.info("Analyzing marketplace entry...")
        
        # Look for marketplace JSON
        marketplace_paths = [
            self.project_path / "marketplace",
            self.project_path / "src" / "marketplace",
            self.project_path / "config" / "marketplace"
        ]
        
        marketplace_found = False
        for marketplace_path in marketplace_paths:
            if marketplace_path.exists():
                json_files = list(marketplace_path.glob("*.json"))
                if json_files:
                    self.analysis.artifacts.append(ProjectArtifact(
                        name="Marketplace Entry",
                        path=marketplace_path,
                        status="present",
                        description=f"Found {len(json_files)} marketplace JSON files",
                        priority="medium",
                        details={"marketplace_files": [f.name for f in json_files]}
                    ))
                    marketplace_found = True
                    break
        
        if not marketplace_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Marketplace Entry",
                path=self.project_path / "marketplace",
                status="missing",
                description="No marketplace entry found",
                priority="medium"
            ))
    
    def _analyze_onboarding_docs(self):
        """Analyze onboarding documentation"""
        logger.info("Analyzing onboarding documentation...")
        
        # Look for common documentation files
        doc_files = [
            "README.md",
            "ONBOARDING.md",
            "SETUP.md",
            "INSTALL.md",
            "docs/README.md",
            "docs/onboarding.md"
        ]
        
        docs_found = []
        for doc_file in doc_files:
            doc_path = self.project_path / doc_file
            if doc_path.exists():
                docs_found.append(doc_file)
        
        if docs_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Onboarding Documentation",
                path=self.project_path / "README.md",
                status="present",
                description=f"Found documentation: {', '.join(docs_found)}",
                priority="low",
                details={"doc_files": docs_found}
            ))
        else:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Onboarding Documentation",
                path=self.project_path / "README.md",
                status="missing",
                description="No onboarding documentation found",
                priority="low"
            ))
    
    def _analyze_tests(self):
        """Analyze test files"""
        logger.info("Analyzing test files...")
        
        # Look for test directories
        test_paths = [
            self.project_path / "tests",
            self.project_path / "test",
            self.project_path / "src" / "tests"
        ]
        
        tests_found = False
        for test_path in test_paths:
            if test_path.exists():
                test_files = list(test_path.rglob("test_*.py"))
                if test_files:
                    self.analysis.artifacts.append(ProjectArtifact(
                        name="Test Files",
                        path=test_path,
                        status="present",
                        description=f"Found {len(test_files)} test files",
                        priority="medium",
                        details={"test_count": len(test_files)}
                    ))
                    tests_found = True
                    break
        
        if not tests_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Test Files",
                path=self.project_path / "tests",
                status="missing",
                description="No test files found",
                priority="medium"
            ))
    
    def _analyze_models(self):
        """Analyze data models"""
        logger.info("Analyzing data models...")
        
        # Look for model files
        model_paths = [
            self.project_path / "src" / "models.py",
            self.project_path / "models.py",
            self.project_path / "src" / "models",
            self.project_path / "models"
        ]
        
        models_found = False
        for model_path in model_paths:
            if model_path.exists():
                if model_path.is_file():
                    self.analysis.artifacts.append(ProjectArtifact(
                        name="Data Models",
                        path=model_path,
                        status="present",
                        description="Data models file found",
                        priority="high"
                    ))
                    models_found = True
                    break
                elif model_path.is_dir():
                    model_files = list(model_path.rglob("*.py"))
                    if model_files:
                        self.analysis.artifacts.append(ProjectArtifact(
                            name="Data Models",
                            path=model_path,
                            status="present",
                            description=f"Found {len(model_files)} model files",
                            priority="high",
                            details={"model_count": len(model_files)}
                        ))
                        models_found = True
                        break
        
        if not models_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Data Models",
                path=self.project_path / "src" / "models.py",
                status="missing",
                description="No data models found",
                priority="high"
            ))
    
    def _analyze_seed_data(self):
        """Analyze seed data files"""
        logger.info("Analyzing seed data...")
        
        # Look for seed files
        seed_paths = [
            self.project_path / "src" / "seed.py",
            self.project_path / "seed.py",
            self.project_path / "data" / "seed.py",
            self.project_path / "fixtures"
        ]
        
        seed_found = False
        for seed_path in seed_paths:
            if seed_path.exists():
                self.analysis.artifacts.append(ProjectArtifact(
                    name="Seed Data",
                    path=seed_path,
                    status="present",
                    description="Seed data found",
                    priority="medium"
                ))
                seed_found = True
                break
        
        if not seed_found:
            self.analysis.artifacts.append(ProjectArtifact(
                name="Seed Data",
                path=self.project_path / "src" / "seed.py",
                status="missing",
                description="No seed data found",
                priority="medium"
            ))
    
    def _calculate_compatibility_score(self):
        """Calculate SBH compatibility score"""
        total_artifacts = len(self.analysis.artifacts)
        present_artifacts = len([a for a in self.analysis.artifacts if a.status == "present"])
        
        if total_artifacts > 0:
            self.analysis.sbh_compatibility_score = present_artifacts / total_artifacts
        else:
            self.analysis.sbh_compatibility_score = 0.0
        
        # Identify missing components
        missing_artifacts = [a for a in self.analysis.artifacts if a.status == "missing"]
        self.analysis.missing_components = [a.name for a in missing_artifacts]
    
    def _generate_recommendations(self):
        """Generate recommendations for improving SBH compatibility"""
        logger.info("Generating recommendations...")
        
        recommendations = []
        
        # High priority recommendations
        high_priority_missing = [a for a in self.analysis.artifacts 
                               if a.status == "missing" and a.priority == "high"]
        
        for artifact in high_priority_missing:
            recommendations.append(f"🔴 HIGH PRIORITY: Add {artifact.name} at {artifact.path}")
        
        # Medium priority recommendations
        medium_priority_missing = [a for a in self.analysis.artifacts 
                                 if a.status == "missing" and a.priority == "medium"]
        
        for artifact in medium_priority_missing:
            recommendations.append(f"🟡 MEDIUM PRIORITY: Add {artifact.name} at {artifact.path}")
        
        # General recommendations
        if self.analysis.sbh_compatibility_score < 0.5:
            recommendations.append("⚠️  Project has low SBH compatibility - consider restructuring")
        elif self.analysis.sbh_compatibility_score < 0.8:
            recommendations.append("🟢 Project has good SBH compatibility - minor improvements needed")
        else:
            recommendations.append("✅ Project has excellent SBH compatibility!")
        
        self.analysis.recommendations = recommendations
    
    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a human-readable analysis report"""
        if output_path is None:
            output_path = self.project_path / "resume.report.md"
        
        report_lines = [
            "# SBH Project Resume Analysis Report",
            "",
            f"**Project:** {self.analysis.project_name}",
            f"**Path:** {self.analysis.project_path}",
            f"**SBH Compatibility Score:** {self.analysis.sbh_compatibility_score:.1%}",
            "",
            "## Artifacts Analysis",
            ""
        ]
        
        # Group artifacts by status
        present_artifacts = [a for a in self.analysis.artifacts if a.status == "present"]
        missing_artifacts = [a for a in self.analysis.artifacts if a.status == "missing"]
        
        if present_artifacts:
            report_lines.extend([
                "### ✅ Present Artifacts",
                ""
            ])
            for artifact in present_artifacts:
                report_lines.append(f"- **{artifact.name}** ({artifact.priority} priority)")
                report_lines.append(f"  - Path: `{artifact.path}`")
                report_lines.append(f"  - Description: {artifact.description}")
                if artifact.details:
                    for key, value in artifact.details.items():
                        report_lines.append(f"  - {key}: {value}")
                report_lines.append("")
        
        if missing_artifacts:
            report_lines.extend([
                "### ❌ Missing Artifacts",
                ""
            ])
            for artifact in missing_artifacts:
                report_lines.append(f"- **{artifact.name}** ({artifact.priority} priority)")
                report_lines.append(f"  - Expected Path: `{artifact.path}`")
                report_lines.append(f"  - Description: {artifact.description}")
                report_lines.append("")
        
        if self.analysis.recommendations:
            report_lines.extend([
                "## Recommendations",
                ""
            ])
            for recommendation in self.analysis.recommendations:
                report_lines.append(f"- {recommendation}")
            report_lines.append("")
        
        report_lines.extend([
            "## Next Steps",
            "",
            "To complete SBH integration, run:",
            f"```bash",
            f"python -m src.cli project resume {self.project_path}",
            f"```",
            "",
            "This will auto-generate missing components and integrate the project with SBH."
        ])
        
        report_content = "\n".join(report_lines)
        
        # Write report to file
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        return report_content
