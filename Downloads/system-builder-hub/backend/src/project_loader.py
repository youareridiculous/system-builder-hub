"""
📂 System Build Hub OS - Project Loader

This module enables loading existing projects, analyzing their structure,
inferring build phases, and generating completion plans.
"""

import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from parser import parse_file, get_supported_extensions
from system_lifecycle import SystemLifecycleManager, SystemStage, SystemStatus, SystemMetadata
from agent_framework import AgentOrchestrator, MemorySystem

class ProjectType(Enum):
    WEB_APP = "web_app"
    API_SERVICE = "api_service"
    MOBILE_APP = "mobile_app"
    DESKTOP_APP = "desktop_app"
    LIBRARY = "library"
    CLI_TOOL = "cli_tool"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"

class BuildPhase(Enum):
    SETUP = "setup"
    PLANNING = "planning"
    CORE_DEVELOPMENT = "core_development"
    INTEGRATION = "integration"
    TESTING = "testing"
    DEPLOYMENT_READY = "deployment_ready"
    PRODUCTION = "production"

@dataclass
class ProjectAnalysis:
    """Analysis results for an existing project"""
    project_type: ProjectType
    build_phase: BuildPhase
    technologies: List[str]
    file_structure: Dict[str, Any]
    dependencies: List[str]
    configuration_files: List[str]
    test_files: List[str]
    documentation_files: List[str]
    estimated_completion: float  # 0-100%
    missing_components: List[str]
    next_steps: List[str]
    complexity_score: int  # 1-10

@dataclass
class CompletionPlan:
    """Plan to complete an existing project"""
    id: str
    system_id: str
    current_phase: BuildPhase
    target_phase: BuildPhase
    tasks: List[Dict[str, Any]]
    estimated_duration: str
    priority_order: List[str]
    dependencies: List[str]
    created_at: datetime

class ProjectLoader:
    """
    Loads existing projects and generates completion plans
    """
    
    def __init__(self, base_dir: Path, system_lifecycle: SystemLifecycleManager, 
                 agent_orchestrator: AgentOrchestrator, memory_system: MemorySystem):
        self.base_dir = base_dir
        self.projects_dir = base_dir / "projects"
        self.system_lifecycle = system_lifecycle
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        
        # Create projects directory
        self.projects_dir.mkdir(exist_ok=True)
    
    def load_existing_project(self, project_path: Path, context: Dict[str, Any]) -> str:
        """
        Load existing project and create system
        
        Args:
            project_path: Path to existing project directory
            context: Additional context about the project
            
        Returns:
            System ID of the created system
        """
        try:
            # Validate project path
            if not project_path.exists() or not project_path.is_dir():
                raise ValueError(f"Project path does not exist or is not a directory: {project_path}")
            
            # Analyze project structure
            analysis = self.analyze_project_structure(project_path)
            
            # Create system metadata
            system_name = context.get("name", project_path.name)
            description = context.get("description", f"Loaded existing project: {project_path.name}")
            tags = context.get("tags", [])
            owner = context.get("owner", "default")
            
            # Determine initial stage based on analysis
            initial_stage = self._map_phase_to_stage(analysis.build_phase)
            
            # Create system in lifecycle manager
            system_id = self.system_lifecycle.create_system(
                name=system_name,
                description=description,
                tags=tags + [analysis.project_type.value],
                stack=analysis.technologies,
                owner=owner,
                estimated_complexity=analysis.complexity_score,
                initial_stage=initial_stage
            )
            
            # Copy project files to system directory
            system_dir = self.base_dir / "memory" / "systems" / system_id
            system_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy project files
            self._copy_project_files(project_path, system_dir)
            
            # Generate completion plan
            completion_plan = self.generate_completion_plan(system_id, analysis, context)
            
            # Log the project loading event
            self.memory_system.log_event("project_loaded", {
                "system_id": system_id,
                "original_path": str(project_path),
                "analysis": asdict(analysis),
                "context": context,
                "completion_plan_id": completion_plan.id
            })
            
            return system_id
            
        except Exception as e:
            raise Exception(f"Failed to load project: {str(e)}")
    
    def analyze_project_structure(self, project_path: Path) -> ProjectAnalysis:
        """
        Analyze project structure and infer build phase
        
        Args:
            project_path: Path to project directory
            
        Returns:
            ProjectAnalysis with detailed analysis results
        """
        try:
            # Get all files in project
            all_files = list(project_path.rglob("*"))
            files = [f for f in all_files if f.is_file()]
            
            # Analyze file types and structure
            file_extensions = [f.suffix.lower() for f in files]
            file_names = [f.name.lower() for f in files]
            
            # Detect project type
            project_type = self._detect_project_type(file_extensions, file_names, project_path)
            
            # Detect technologies
            technologies = self._detect_technologies(file_extensions, file_names)
            
            # Analyze file structure
            file_structure = self._analyze_file_structure(project_path, files)
            
            # Detect dependencies
            dependencies = self._detect_dependencies(project_path, file_names)
            
            # Categorize files
            config_files = [f.name for f in files if self._is_config_file(f.name)]
            test_files = [f.name for f in files if self._is_test_file(f.name)]
            doc_files = [f.name for f in files if self._is_documentation_file(f.name)]
            
            # Determine build phase
            build_phase = self._determine_build_phase(
                file_structure, config_files, test_files, doc_files, technologies
            )
            
            # Calculate completion percentage
            completion = self._calculate_completion_percentage(build_phase, file_structure)
            
            # Identify missing components
            missing_components = self._identify_missing_components(project_type, build_phase, file_structure)
            
            # Generate next steps
            next_steps = self._generate_next_steps(build_phase, missing_components, technologies)
            
            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(file_structure, technologies, dependencies)
            
            return ProjectAnalysis(
                project_type=project_type,
                build_phase=build_phase,
                technologies=technologies,
                file_structure=file_structure,
                dependencies=dependencies,
                configuration_files=config_files,
                test_files=test_files,
                documentation_files=doc_files,
                estimated_completion=completion,
                missing_components=missing_components,
                next_steps=next_steps,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            raise Exception(f"Failed to analyze project structure: {str(e)}")
    
    def generate_completion_plan(self, system_id: str, analysis: ProjectAnalysis, 
                                context: Dict[str, Any]) -> CompletionPlan:
        """
        Generate plan to complete existing project
        
        Args:
            system_id: ID of the system
            analysis: Project analysis results
            context: Additional context
            
        Returns:
            CompletionPlan with detailed tasks and timeline
        """
        try:
            # Determine target phase based on context
            target_phase = self._determine_target_phase(analysis.build_phase, context)
            
            # Generate tasks based on current and target phases
            tasks = self._generate_tasks(analysis, target_phase, context)
            
            # Estimate duration
            estimated_duration = self._estimate_duration(tasks, analysis.complexity_score)
            
            # Determine priority order
            priority_order = self._determine_priority_order(tasks, analysis.missing_components)
            
            # Identify dependencies
            dependencies = self._identify_task_dependencies(tasks)
            
            # Create completion plan
            plan = CompletionPlan(
                id=f"plan-{uuid.uuid4().hex[:8]}",
                system_id=system_id,
                current_phase=analysis.build_phase,
                target_phase=target_phase,
                tasks=tasks,
                estimated_duration=estimated_duration,
                priority_order=priority_order,
                dependencies=dependencies,
                created_at=datetime.now()
            )
            
            # Save completion plan
            self._save_completion_plan(plan)
            
            return plan
            
        except Exception as e:
            raise Exception(f"Failed to generate completion plan: {str(e)}")
    
    def inject_context(self, system_id: str, context: Dict[str, Any]) -> bool:
        """
        Inject additional context mid-build
        
        Args:
            system_id: ID of the system
            context: Additional context to inject
            
        Returns:
            True if successful
        """
        try:
            # Update system metadata - this would need to be implemented in system_lifecycle
            # For now, we'll just log the context injection
            
            # Log context injection
            self.memory_system.log_event("context_injected", {
                "system_id": system_id,
                "context": context,
                "timestamp": datetime.now().isoformat()
            })
            
            # Regenerate completion plan if needed
            if context.get("regenerate_plan", False):
                system_metadata = self.system_lifecycle.get_system_metadata(system_id)
                system_dir = self.base_dir / "memory" / "systems" / system_id
                
                if system_dir.exists():
                    analysis = self.analyze_project_structure(system_dir)
                    self.generate_completion_plan(system_id, analysis, context)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to inject context: {str(e)}")
    
    def _copy_project_files(self, source_path: Path, dest_path: Path):
        """Copy project files to system directory"""
        try:
            # Copy all files and directories
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
        except Exception as e:
            raise Exception(f"Failed to copy project files: {str(e)}")
    
    def _detect_project_type(self, extensions: List[str], file_names: List[str], 
                            project_path: Path) -> ProjectType:
        """Detect project type based on files and structure"""
        # Check for specific project indicators
        if any("package.json" in name for name in file_names):
            return ProjectType.WEB_APP
        elif any("requirements.txt" in name or "pyproject.toml" in name for name in file_names):
            return ProjectType.API_SERVICE
        elif any("pubspec.yaml" in name for name in file_names):
            return ProjectType.MOBILE_APP
        elif any("Cargo.toml" in name for name in file_names):
            return ProjectType.LIBRARY
        elif any("go.mod" in name for name in file_names):
            return ProjectType.CLI_TOOL
        elif any("dockerfile" in name or "docker-compose" in name for name in file_names):
            return ProjectType.INFRASTRUCTURE
        else:
            return ProjectType.UNKNOWN
    
    def _detect_technologies(self, extensions: List[str], file_names: List[str]) -> List[str]:
        """Detect technologies used in the project"""
        technologies = []
        
        # Language detection
        if ".py" in extensions:
            technologies.append("python")
        if ".js" in extensions or ".ts" in extensions:
            technologies.append("javascript")
        if ".java" in extensions:
            technologies.append("java")
        if ".go" in extensions:
            technologies.append("go")
        if ".rs" in extensions:
            technologies.append("rust")
        
        # Framework detection
        if "package.json" in file_names:
            technologies.append("nodejs")
        if "requirements.txt" in file_names:
            technologies.append("pip")
        if "dockerfile" in file_names:
            technologies.append("docker")
        if "kubernetes" in file_names or ".yaml" in extensions:
            technologies.append("kubernetes")
        
        return list(set(technologies))
    
    def _analyze_file_structure(self, project_path: Path, files: List[Path]) -> Dict[str, Any]:
        """Analyze the file structure of the project"""
        structure = {
            "total_files": len(files),
            "directories": [],
            "file_types": {},
            "main_files": [],
            "config_files": [],
            "test_files": [],
            "documentation": []
        }
        
        # Count file types
        for file in files:
            ext = file.suffix.lower()
            structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1
        
        # Identify main files
        main_indicators = ["main.py", "app.py", "index.js", "main.go", "main.rs"]
        structure["main_files"] = [f.name for f in files if f.name in main_indicators]
        
        return structure
    
    def _detect_dependencies(self, project_path: Path, file_names: List[str]) -> List[str]:
        """Detect project dependencies"""
        dependencies = []
        
        # Check for dependency files
        dependency_files = ["requirements.txt", "package.json", "go.mod", "Cargo.toml", "pubspec.yaml"]
        for dep_file in dependency_files:
            if dep_file in file_names:
                dependencies.append(dep_file)
        
        return dependencies
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_patterns = [".config", ".conf", ".ini", ".yaml", ".yml", ".json", ".env", ".toml"]
        return any(pattern in filename.lower() for pattern in config_patterns)
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file"""
        test_patterns = ["test_", "_test", ".test.", ".spec."]
        return any(pattern in filename.lower() for pattern in test_patterns)
    
    def _is_documentation_file(self, filename: str) -> bool:
        """Check if file is a documentation file"""
        doc_patterns = ["readme", "docs", ".md", ".rst", ".txt"]
        return any(pattern in filename.lower() for pattern in doc_patterns)
    
    def _determine_build_phase(self, file_structure: Dict[str, Any], config_files: List[str],
                              test_files: List[str], doc_files: List[str], 
                              technologies: List[str]) -> BuildPhase:
        """Determine the current build phase"""
        total_files = file_structure["total_files"]
        main_files = file_structure["main_files"]
        
        # Very early stage
        if total_files < 5:
            return BuildPhase.SETUP
        
        # Has main files but no tests
        if main_files and not test_files:
            return BuildPhase.CORE_DEVELOPMENT
        
        # Has tests but no deployment config
        if test_files and not config_files:
            return BuildPhase.TESTING
        
        # Has deployment config
        if config_files:
            return BuildPhase.DEPLOYMENT_READY
        
        return BuildPhase.CORE_DEVELOPMENT
    
    def _calculate_completion_percentage(self, build_phase: BuildPhase, 
                                       file_structure: Dict[str, Any]) -> float:
        """Calculate estimated completion percentage"""
        phase_completion = {
            BuildPhase.SETUP: 10,
            BuildPhase.PLANNING: 20,
            BuildPhase.CORE_DEVELOPMENT: 50,
            BuildPhase.INTEGRATION: 70,
            BuildPhase.TESTING: 85,
            BuildPhase.DEPLOYMENT_READY: 95,
            BuildPhase.PRODUCTION: 100
        }
        
        base_completion = phase_completion.get(build_phase, 50)
        
        # Adjust based on file count
        total_files = file_structure["total_files"]
        if total_files > 50:
            base_completion += 10
        elif total_files > 20:
            base_completion += 5
        
        return min(base_completion, 100)
    
    def _identify_missing_components(self, project_type: ProjectType, build_phase: BuildPhase,
                                   file_structure: Dict[str, Any]) -> List[str]:
        """Identify missing components based on project type and phase"""
        missing = []
        
        if project_type == ProjectType.WEB_APP:
            if build_phase in [BuildPhase.SETUP, BuildPhase.PLANNING]:
                missing.extend(["package.json", "README.md", "src/ directory"])
            elif build_phase == BuildPhase.CORE_DEVELOPMENT:
                missing.extend(["tests/", "docs/", "configuration"])
            elif build_phase == BuildPhase.TESTING:
                missing.extend(["deployment config", "CI/CD pipeline"])
        
        elif project_type == ProjectType.API_SERVICE:
            if build_phase in [BuildPhase.SETUP, BuildPhase.PLANNING]:
                missing.extend(["requirements.txt", "app.py", "README.md"])
            elif build_phase == BuildPhase.CORE_DEVELOPMENT:
                missing.extend(["tests/", "API documentation", "environment config"])
            elif build_phase == BuildPhase.TESTING:
                missing.extend(["Dockerfile", "deployment scripts"])
        
        return missing
    
    def _generate_next_steps(self, build_phase: BuildPhase, missing_components: List[str],
                            technologies: List[str]) -> List[str]:
        """Generate next steps based on current phase and missing components"""
        steps = []
        
        if build_phase == BuildPhase.SETUP:
            steps.extend([
                "Initialize project structure",
                "Set up development environment",
                "Create basic configuration files"
            ])
        
        elif build_phase == BuildPhase.CORE_DEVELOPMENT:
            steps.extend([
                "Implement core functionality",
                "Add error handling",
                "Create basic tests"
            ])
        
        elif build_phase == BuildPhase.TESTING:
            steps.extend([
                "Write comprehensive tests",
                "Add integration tests",
                "Set up CI/CD pipeline"
            ])
        
        # Add specific steps for missing components
        for component in missing_components:
            steps.append(f"Add {component}")
        
        return steps
    
    def _calculate_complexity_score(self, file_structure: Dict[str, Any], 
                                  technologies: List[str], dependencies: List[str]) -> int:
        """Calculate complexity score (1-10)"""
        score = 1
        
        # File count factor
        total_files = file_structure["total_files"]
        if total_files > 100:
            score += 3
        elif total_files > 50:
            score += 2
        elif total_files > 20:
            score += 1
        
        # Technology factor
        score += min(len(technologies), 3)
        
        # Dependencies factor
        score += min(len(dependencies), 2)
        
        return min(score, 10)
    
    def _map_phase_to_stage(self, build_phase: BuildPhase) -> SystemStage:
        """Map build phase to system stage"""
        mapping = {
            BuildPhase.SETUP: SystemStage.IDEA,
            BuildPhase.PLANNING: SystemStage.PLAN,
            BuildPhase.CORE_DEVELOPMENT: SystemStage.BUILD,
            BuildPhase.INTEGRATION: SystemStage.BUILD,
            BuildPhase.TESTING: SystemStage.TEST,
            BuildPhase.DEPLOYMENT_READY: SystemStage.DEPLOY,
            BuildPhase.PRODUCTION: SystemStage.MAINTAIN
        }
        return mapping.get(build_phase, SystemStage.BUILD)
    
    def _determine_target_phase(self, current_phase: BuildPhase, context: Dict[str, Any]) -> BuildPhase:
        """Determine target phase based on context"""
        target = context.get("target_phase")
        if target:
            return BuildPhase(target)
        
        # Default progression
        phase_progression = {
            BuildPhase.SETUP: BuildPhase.CORE_DEVELOPMENT,
            BuildPhase.PLANNING: BuildPhase.CORE_DEVELOPMENT,
            BuildPhase.CORE_DEVELOPMENT: BuildPhase.TESTING,
            BuildPhase.INTEGRATION: BuildPhase.TESTING,
            BuildPhase.TESTING: BuildPhase.DEPLOYMENT_READY,
            BuildPhase.DEPLOYMENT_READY: BuildPhase.PRODUCTION,
            BuildPhase.PRODUCTION: BuildPhase.PRODUCTION
        }
        
        return phase_progression.get(current_phase, BuildPhase.PRODUCTION)
    
    def _generate_tasks(self, analysis: ProjectAnalysis, target_phase: BuildPhase,
                       context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tasks to reach target phase"""
        tasks = []
        
        # Generate tasks based on missing components
        for component in analysis.missing_components:
            tasks.append({
                "id": f"task-{uuid.uuid4().hex[:8]}",
                "title": f"Add {component}",
                "description": f"Implement or configure {component}",
                "priority": "high" if "test" in component.lower() else "medium",
                "estimated_hours": 2,
                "dependencies": [],
                "assigned_agent": "builder"
            })
        
        # Generate tasks based on phase transition
        if target_phase == BuildPhase.TESTING:
            tasks.append({
                "id": f"task-{uuid.uuid4().hex[:8]}",
                "title": "Set up testing framework",
                "description": "Configure and implement comprehensive testing",
                "priority": "high",
                "estimated_hours": 4,
                "dependencies": [],
                "assigned_agent": "tester"
            })
        
        elif target_phase == BuildPhase.DEPLOYMENT_READY:
            tasks.append({
                "id": f"task-{uuid.uuid4().hex[:8]}",
                "title": "Configure deployment",
                "description": "Set up deployment configuration and scripts",
                "priority": "high",
                "estimated_hours": 3,
                "dependencies": [],
                "assigned_agent": "infra"
            })
        
        return tasks
    
    def _estimate_duration(self, tasks: List[Dict[str, Any]], complexity_score: int) -> str:
        """Estimate total duration for completion"""
        total_hours = sum(task.get("estimated_hours", 2) for task in tasks)
        
        # Adjust for complexity
        adjusted_hours = total_hours * (complexity_score / 5)
        
        if adjusted_hours < 8:
            return f"{adjusted_hours:.1f} hours"
        elif adjusted_hours < 40:
            return f"{adjusted_hours/8:.1f} days"
        else:
            return f"{adjusted_hours/40:.1f} weeks"
    
    def _determine_priority_order(self, tasks: List[Dict[str, Any]], 
                                missing_components: List[str]) -> List[str]:
        """Determine priority order for tasks"""
        # Sort by priority and dependencies
        high_priority = [task["id"] for task in tasks if task.get("priority") == "high"]
        medium_priority = [task["id"] for task in tasks if task.get("priority") == "medium"]
        low_priority = [task["id"] for task in tasks if task.get("priority") == "low"]
        
        return high_priority + medium_priority + low_priority
    
    def _identify_task_dependencies(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """Identify dependencies between tasks"""
        dependencies = []
        for task in tasks:
            task_deps = task.get("dependencies", [])
            dependencies.extend(task_deps)
        return list(set(dependencies))
    
    def _save_completion_plan(self, plan: CompletionPlan):
        """Save completion plan to file"""
        plans_file = self.base_dir / "completion_plans.json"
        
        # Load existing plans
        plans = []
        if plans_file.exists():
            try:
                with open(plans_file, 'r') as f:
                    plans = json.load(f)
            except:
                plans = []
        
        # Add new plan
        plan_dict = asdict(plan)
        plan_dict["created_at"] = plan.created_at.isoformat()
        plans.append(plan_dict)
        
        # Save plans
        with open(plans_file, 'w') as f:
            json.dump(plans, f, indent=2)
