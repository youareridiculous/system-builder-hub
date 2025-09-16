"""
🚀 System Build Hub OS - Prompt-to-Build Engine

This module provides the core interface for converting natural language
prompts into executable build commands through AI agent orchestration.
"""

import re
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from system_lifecycle import SystemStage

class BuildCommandType(Enum):
    BUILD_SYSTEM = "build_system"
    GENERATE_CODE = "generate_code"
    CREATE_UI = "create_ui"
    SETUP_INFRA = "setup_infra"
    PARSE_DOCUMENTS = "parse_documents"
    CUSTOM = "custom"

class BuildContext(Enum):
    NEW_PROJECT = "new_project"
    CURRENT_SESSION = "current_session"
    EXISTING_SYSTEM = "existing_system"

@dataclass
class ParsedCommand:
    """Parsed build command from natural language"""
    original_prompt: str
    command_type: BuildCommandType
    system_name: str
    description: str
    technologies: List[str]
    features: List[str]
    context: BuildContext
    priority: int
    estimated_complexity: int
    dependencies: List[str]
    metadata: Dict[str, Any]

@dataclass
class BuildSpecification:
    """Detailed specification for a build task"""
    id: str
    command: ParsedCommand
    task_breakdown: List[Dict[str, Any]]
    architecture_plan: Dict[str, Any]
    file_structure: List[str]
    api_endpoints: List[Dict[str, Any]]
    database_schema: Optional[Dict[str, Any]]
    deployment_config: Optional[Dict[str, Any]]
    created_at: datetime
    status: str  # "draft", "approved", "in_progress", "completed"

class PromptBuildEngine:
    """
    Core engine for converting prompts to build specifications
    """
    
    def __init__(self, agent_orchestrator, system_lifecycle, memory_system):
        self.agent_orchestrator = agent_orchestrator
        self.system_lifecycle = system_lifecycle
        self.memory_system = memory_system
        
        # Command patterns for parsing
        self.command_patterns = {
            BuildCommandType.BUILD_SYSTEM: [
                r"/build\s+(.+?)\s+(?:with|using)\s+(.+)",
                r"create\s+(.+?)\s+system\s+(?:with|using)\s+(.+)",
                r"build\s+(.+?)\s+application\s+(?:with|using)\s+(.+)"
            ],
            BuildCommandType.GENERATE_CODE: [
                r"/generate\s+(.+?)\s+(?:in|using)\s+(.+)",
                r"create\s+(.+?)\s+code\s+(?:in|using)\s+(.+)",
                r"generate\s+(.+?)\s+module\s+(?:in|using)\s+(.+)"
            ],
            BuildCommandType.CREATE_UI: [
                r"/create\s+(.+?)\s+ui\s+(?:in|using)\s+(.+)",
                r"build\s+(.+?)\s+interface\s+(?:in|using)\s+(.+)",
                r"design\s+(.+?)\s+frontend\s+(?:in|using)\s+(.+)"
            ],
            BuildCommandType.SETUP_INFRA: [
                r"/setup\s+(.+?)\s+infrastructure\s+(?:with|using)\s+(.+)",
                r"deploy\s+(.+?)\s+to\s+(.+)",
                r"configure\s+(.+?)\s+environment\s+(?:with|using)\s+(.+)"
            ],
            BuildCommandType.PARSE_DOCUMENTS: [
                r"/parse\s+(.+?)\s+documents\s+(?:with|using)\s+(.+)",
                r"extract\s+(.+?)\s+from\s+(.+)",
                r"analyze\s+(.+?)\s+files\s+(?:with|using)\s+(.+)"
            ]
        }
        
        # Technology detection patterns
        self.tech_patterns = {
            "frontend": ["react", "vue", "angular", "svelte", "tailwind", "bootstrap", "css", "html", "javascript", "typescript"],
            "backend": ["python", "flask", "django", "fastapi", "node", "express", "java", "spring", "go", "rust"],
            "database": ["postgresql", "mysql", "mongodb", "redis", "sqlite", "supabase", "firebase"],
            "ai": ["openai", "gpt", "claude", "gemini", "llama", "ollama", "huggingface", "transformers"],
            "cloud": ["aws", "azure", "gcp", "vercel", "netlify", "heroku", "docker", "kubernetes"],
            "auth": ["oauth", "jwt", "github", "google", "facebook", "email", "password"]
        }
    
    def parse_prompt(self, prompt: str, context: BuildContext = BuildContext.NEW_PROJECT) -> ParsedCommand:
        """
        Parse a natural language prompt into a structured build command
        """
        
        prompt_lower = prompt.lower()
        
        # Determine command type
        command_type = self._detect_command_type(prompt_lower)
        
        # Extract system name and description
        system_name, description = self._extract_system_info(prompt)
        
        # Detect technologies
        technologies = self._detect_technologies(prompt_lower)
        
        # Extract features
        features = self._extract_features(prompt_lower)
        
        # Estimate complexity
        estimated_complexity = self._estimate_complexity(technologies, features)
        
        # Determine priority
        priority = self._determine_priority(prompt_lower)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(prompt_lower)
        
        return ParsedCommand(
            original_prompt=prompt,
            command_type=command_type,
            system_name=system_name,
            description=description,
            technologies=technologies,
            features=features,
            context=context,
            priority=priority,
            estimated_complexity=estimated_complexity,
            dependencies=dependencies,
            metadata={
                "parsed_at": datetime.now().isoformat(),
                "confidence_score": self._calculate_confidence(prompt_lower, command_type)
            }
        )
    
    def _detect_command_type(self, prompt: str) -> BuildCommandType:
        """Detect the type of build command from the prompt"""
        
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt):
                    return command_type
        
        # Default to custom if no pattern matches
        return BuildCommandType.CUSTOM
    
    def _extract_system_info(self, prompt: str) -> Tuple[str, str]:
        """Extract system name and description from prompt"""
        
        # Try to extract system name from common patterns
        name_patterns = [
            r"build\s+([a-zA-Z0-9\s]+?)\s+(?:system|application|app)",
            r"create\s+([a-zA-Z0-9\s]+?)\s+(?:system|application|app)",
            r"generate\s+([a-zA-Z0-9\s]+?)\s+(?:system|application|app)",
            r"setup\s+([a-zA-Z0-9\s]+?)\s+(?:system|application|app)"
        ]
        
        system_name = "Untitled System"
        for pattern in name_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                system_name = match.group(1).strip()
                break
        
        # Use the prompt as description, cleaned up
        description = prompt.replace("/build", "").replace("/generate", "").replace("/create", "").strip()
        
        return system_name, description
    
    def _detect_technologies(self, prompt: str) -> List[str]:
        """Detect technologies mentioned in the prompt"""
        
        detected_techs = []
        
        for category, techs in self.tech_patterns.items():
            for tech in techs:
                if tech in prompt:
                    detected_techs.append(tech)
        
        return list(set(detected_techs))  # Remove duplicates
    
    def _extract_features(self, prompt: str) -> List[str]:
        """Extract features from the prompt"""
        
        feature_keywords = [
            "authentication", "auth", "login", "signup", "oauth", "jwt",
            "database", "api", "rest", "graphql", "websocket", "real-time",
            "file upload", "upload", "download", "search", "filter", "sort",
            "dashboard", "admin", "user management", "notifications",
            "email", "sms", "payment", "stripe", "paypal", "analytics",
            "logging", "monitoring", "deployment", "docker", "kubernetes"
        ]
        
        features = []
        for feature in feature_keywords:
            if feature in prompt:
                features.append(feature)
        
        return features
    
    def _estimate_complexity(self, technologies: List[str], features: List[str]) -> int:
        """Estimate complexity on a 1-10 scale"""
        
        base_complexity = 3
        
        # Add complexity for each technology category
        tech_categories = set()
        for tech in technologies:
            for category, techs in self.tech_patterns.items():
                if tech in techs:
                    tech_categories.add(category)
        
        complexity = base_complexity + len(tech_categories)
        
        # Add complexity for features
        complexity += len(features) * 0.5
        
        # Cap at 10
        return min(int(complexity), 10)
    
    def _determine_priority(self, prompt: str) -> int:
        """Determine priority based on urgency indicators"""
        
        urgency_indicators = ["urgent", "asap", "quick", "fast", "immediate", "now"]
        priority_indicators = ["high priority", "important", "critical"]
        
        if any(indicator in prompt for indicator in urgency_indicators):
            return 9
        elif any(indicator in prompt for indicator in priority_indicators):
            return 7
        else:
            return 5
    
    def _extract_dependencies(self, prompt: str) -> List[str]:
        """Extract dependencies from the prompt"""
        
        dependency_patterns = [
            r"depends on\s+([^,]+)",
            r"requires\s+([^,]+)",
            r"needs\s+([^,]+)",
            r"with\s+([^,]+)\s+support"
        ]
        
        dependencies = []
        for pattern in dependency_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            dependencies.extend(matches)
        
        return dependencies
    
    def _calculate_confidence(self, prompt: str, command_type: BuildCommandType) -> float:
        """Calculate confidence score for the parsing"""
        
        # Base confidence
        confidence = 0.5
        
        # Boost confidence if we found a clear command pattern
        if command_type != BuildCommandType.CUSTOM:
            confidence += 0.3
        
        # Boost confidence if we detected technologies
        if len(self._detect_technologies(prompt)) > 0:
            confidence += 0.1
        
        # Boost confidence if we detected features
        if len(self._extract_features(prompt)) > 0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def generate_build_spec(self, parsed_command: ParsedCommand) -> BuildSpecification:
        """
        Generate a detailed build specification from a parsed command
        """
        
        spec_id = f"spec-{uuid.uuid4().hex[:8]}"
        
        # Generate task breakdown
        task_breakdown = self._generate_task_breakdown(parsed_command)
        
        # Generate architecture plan
        architecture_plan = self._generate_architecture_plan(parsed_command)
        
        # Generate file structure
        file_structure = self._generate_file_structure(parsed_command)
        
        # Generate API endpoints
        api_endpoints = self._generate_api_endpoints(parsed_command)
        
        # Generate database schema
        database_schema = self._generate_database_schema(parsed_command)
        
        # Generate deployment config
        deployment_config = self._generate_deployment_config(parsed_command)
        
        return BuildSpecification(
            id=spec_id,
            command=parsed_command,
            task_breakdown=task_breakdown,
            architecture_plan=architecture_plan,
            file_structure=file_structure,
            api_endpoints=api_endpoints,
            database_schema=database_schema,
            deployment_config=deployment_config,
            created_at=datetime.now(),
            status="draft"
        )
    
    def _generate_task_breakdown(self, command: ParsedCommand) -> List[Dict[str, Any]]:
        """Generate a breakdown of tasks needed for the build"""
        
        tasks = []
        
        # Project setup tasks
        tasks.append({
            "id": f"task-{uuid.uuid4().hex[:8]}",
            "title": "Project Setup",
            "description": f"Initialize {command.system_name} project structure",
            "type": "setup",
            "priority": command.priority,
            "estimated_duration": "30 minutes",
            "dependencies": []
        })
        
        # Technology-specific tasks
        for tech in command.technologies:
            if tech in ["react", "vue", "angular"]:
                tasks.append({
                    "id": f"task-{uuid.uuid4().hex[:8]}",
                    "title": f"Frontend Setup ({tech})",
                    "description": f"Set up {tech} frontend framework",
                    "type": "frontend",
                    "priority": command.priority,
                    "estimated_duration": "1 hour",
                    "dependencies": ["Project Setup"]
                })
            elif tech in ["flask", "django", "fastapi"]:
                tasks.append({
                    "id": f"task-{uuid.uuid4().hex[:8]}",
                    "title": f"Backend Setup ({tech})",
                    "description": f"Set up {tech} backend framework",
                    "type": "backend",
                    "priority": command.priority,
                    "estimated_duration": "1 hour",
                    "dependencies": ["Project Setup"]
                })
        
        # Feature-specific tasks
        for feature in command.features:
            if "auth" in feature.lower():
                tasks.append({
                    "id": f"task-{uuid.uuid4().hex[:8]}",
                    "title": "Authentication System",
                    "description": "Implement user authentication and authorization",
                    "type": "feature",
                    "priority": command.priority,
                    "estimated_duration": "2 hours",
                    "dependencies": ["Backend Setup"]
                })
            elif "database" in feature.lower():
                tasks.append({
                    "id": f"task-{uuid.uuid4().hex[:8]}",
                    "title": "Database Setup",
                    "description": "Set up database schema and connections",
                    "type": "database",
                    "priority": command.priority,
                    "estimated_duration": "1 hour",
                    "dependencies": ["Backend Setup"]
                })
        
        return tasks
    
    def _generate_architecture_plan(self, command: ParsedCommand) -> Dict[str, Any]:
        """Generate architecture plan for the system"""
        
        architecture = {
            "type": "layered",
            "layers": [],
            "components": [],
            "data_flow": []
        }
        
        # Add layers based on technologies
        if any(tech in command.technologies for tech in ["react", "vue", "angular"]):
            architecture["layers"].append({
                "name": "Frontend",
                "technologies": [tech for tech in command.technologies if tech in ["react", "vue", "angular", "tailwind", "bootstrap"]],
                "responsibilities": ["User Interface", "Client-side Logic", "API Communication"]
            })
        
        if any(tech in command.technologies for tech in ["flask", "django", "fastapi", "node", "express"]):
            architecture["layers"].append({
                "name": "Backend",
                "technologies": [tech for tech in command.technologies if tech in ["flask", "django", "fastapi", "node", "express", "python", "javascript"]],
                "responsibilities": ["API Endpoints", "Business Logic", "Data Processing"]
            })
        
        if any(tech in command.technologies for tech in ["postgresql", "mysql", "mongodb", "redis"]):
            architecture["layers"].append({
                "name": "Data",
                "technologies": [tech for tech in command.technologies if tech in ["postgresql", "mysql", "mongodb", "redis", "sqlite"]],
                "responsibilities": ["Data Storage", "Data Retrieval", "Caching"]
            })
        
        return architecture
    
    def _generate_file_structure(self, command: ParsedCommand) -> List[str]:
        """Generate file structure for the project"""
        
        structure = []
        
        # Base structure
        structure.extend([
            "README.md",
            "requirements.txt",
            ".gitignore",
            "config/",
            "docs/"
        ])
        
        # Frontend structure
        if any(tech in command.technologies for tech in ["react", "vue", "angular"]):
            structure.extend([
                "frontend/",
                "frontend/src/",
                "frontend/src/components/",
                "frontend/src/pages/",
                "frontend/src/utils/",
                "frontend/public/",
                "frontend/package.json"
            ])
        
        # Backend structure
        if any(tech in command.technologies for tech in ["flask", "django", "fastapi"]):
            structure.extend([
                "backend/",
                "backend/app/",
                "backend/app/models/",
                "backend/app/controllers/",
                "backend/app/services/",
                "backend/app/utils/",
                "backend/tests/"
            ])
        
        return structure
    
    def _generate_api_endpoints(self, command: ParsedCommand) -> List[Dict[str, Any]]:
        """Generate API endpoints based on features"""
        
        endpoints = []
        
        # Authentication endpoints
        if any("auth" in feature.lower() for feature in command.features):
            endpoints.extend([
                {
                    "method": "POST",
                    "path": "/api/auth/login",
                    "description": "User login",
                    "parameters": ["email", "password"],
                    "response": "JWT token"
                },
                {
                    "method": "POST",
                    "path": "/api/auth/register",
                    "description": "User registration",
                    "parameters": ["email", "password", "name"],
                    "response": "User object"
                },
                {
                    "method": "GET",
                    "path": "/api/auth/profile",
                    "description": "Get user profile",
                    "parameters": [],
                    "response": "User object"
                }
            ])
        
        # CRUD endpoints for main entities
        endpoints.extend([
            {
                "method": "GET",
                "path": f"/api/{command.system_name.lower().replace(' ', '-')}",
                "description": f"List {command.system_name} items",
                "parameters": ["page", "limit"],
                "response": "Array of items"
            },
            {
                "method": "POST",
                "path": f"/api/{command.system_name.lower().replace(' ', '-')}",
                "description": f"Create {command.system_name} item",
                "parameters": ["data"],
                "response": "Created item"
            }
        ])
        
        return endpoints
    
    def _generate_database_schema(self, command: ParsedCommand) -> Optional[Dict[str, Any]]:
        """Generate database schema based on features"""
        
        if not any("database" in feature.lower() for feature in command.features):
            return None
        
        schema = {
            "tables": []
        }
        
        # User table for authentication
        if any("auth" in feature.lower() for feature in command.features):
            schema["tables"].append({
                "name": "users",
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "email", "type": "VARCHAR(255)", "unique": True},
                    {"name": "password_hash", "type": "VARCHAR(255)"},
                    {"name": "name", "type": "VARCHAR(255)"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                    {"name": "updated_at", "type": "TIMESTAMP"}
                ]
            })
        
        # Main entity table
        main_table_name = command.system_name.lower().replace(' ', '_')
        schema["tables"].append({
            "name": main_table_name,
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "name", "type": "VARCHAR(255)"},
                {"name": "description", "type": "TEXT"},
                {"name": "created_at", "type": "TIMESTAMP"},
                {"name": "updated_at", "type": "TIMESTAMP"}
            ]
        })
        
        return schema
    
    def _generate_deployment_config(self, command: ParsedCommand) -> Optional[Dict[str, Any]]:
        """Generate deployment configuration"""
        
        if not any(tech in command.technologies for tech in ["docker", "kubernetes", "vercel", "netlify"]):
            return None
        
        config = {
            "platform": "docker",  # Default
            "environment": "development",
            "ports": [3000, 5000],
            "volumes": [],
            "environment_variables": []
        }
        
        # Detect platform
        if "vercel" in command.technologies:
            config["platform"] = "vercel"
        elif "netlify" in command.technologies:
            config["platform"] = "netlify"
        elif "kubernetes" in command.technologies:
            config["platform"] = "kubernetes"
        
        return config
    
    def execute_build(self, build_spec: BuildSpecification) -> Dict[str, Any]:
        """
        Execute a build specification through the agent system
        """
        
        # Create system in lifecycle manager
        system_id = self.system_lifecycle.create_system(
            name=build_spec.command.system_name,
            description=build_spec.command.description,
            tags=build_spec.command.technologies,
            stack=build_spec.command.technologies,
            estimated_complexity=build_spec.command.estimated_complexity
        )
        
        # Log the build initiation
        command_dict = asdict(build_spec.command)
        command_dict['command_type'] = build_spec.command.command_type.value
        command_dict['context'] = build_spec.command.context.value
        
        self.memory_system.log_event("build_initiated", {
            "system_id": system_id,
            "spec_id": build_spec.id,
            "command": command_dict,
            "complexity": build_spec.command.estimated_complexity
        })
        
        # Create tasks for each task in breakdown
        created_tasks = []
        for task in build_spec.task_breakdown:
            task_id = self.agent_orchestrator.create_task(
                title=task["title"],
                description=task["description"],
                priority=task["priority"],
                context={
                    "system_id": system_id,
                    "task_type": task["type"],
                    "estimated_duration": task["estimated_duration"]
                }
            )
            
            # Route the task
            assigned_agent = self.agent_orchestrator.route_task(task_id)
            created_tasks.append({
                "task_id": task_id,
                "assigned_agent": assigned_agent,
                "task_info": task
            })
        
        # Update system stage to BUILD
        self.system_lifecycle.update_system_stage(system_id, SystemStage.BUILD, "Build initiated from prompt")
        
        return {
            "system_id": system_id,
            "spec_id": build_spec.id,
            "created_tasks": created_tasks,
            "status": "build_initiated",
            "estimated_completion": "2-4 hours"  # Rough estimate
        }
