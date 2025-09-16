"""
🚀 System Build Hub OS - FastPath Agent

This module provides intelligent build optimization for complex systems,
breaking down bottlenecks into parallelizable modules and orchestrating
subagents for concurrent execution.
"""

import json
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager

class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"

class BottleneckType(Enum):
    COMPUTATION = "computation"
    INTEGRATION = "integration"
    DATA_PROCESSING = "data_processing"
    UI_COMPLEXITY = "ui_complexity"
    INFRASTRUCTURE = "infrastructure"
    AI_MODEL = "ai_model"
    THIRD_PARTY_API = "third_party_api"

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
    ASYNC = "async"
    PIPELINE = "pipeline"

@dataclass
class BuildModule:
    """Represents a modular component of a complex build"""
    module_id: str
    name: str
    description: str
    complexity: ComplexityLevel
    estimated_duration: int  # minutes
    dependencies: List[str]
    required_agents: List[str]
    parallelizable: bool
    priority: int
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    assigned_agent: Optional[str] = None

@dataclass
class BottleneckAnalysis:
    """Analysis of a build bottleneck"""
    bottleneck_id: str
    type: BottleneckType
    description: str
    complexity: ComplexityLevel
    estimated_impact: int  # minutes saved if optimized
    modules: List[BuildModule]
    recommended_mode: ExecutionMode
    optimization_strategy: str
    parallelization_potential: float  # 0.0 to 1.0

@dataclass
class FastPathConfig:
    """Configuration for FastPath optimization"""
    max_parallel_modules: int = 5
    complexity_threshold: ComplexityLevel = ComplexityLevel.MODERATE
    auto_optimize: bool = True
    checkpoint_interval: int = 30  # seconds
    fallback_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    resource_monitoring: bool = True

class FastPathAgent:
    """
    Intelligent agent for optimizing complex builds through parallelization
    and bottleneck analysis
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator, 
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}
        self.module_templates = self._load_module_templates()
        self.bottleneck_patterns = self._load_bottleneck_patterns()
        
    def analyze_build_complexity(self, system_id: str) -> BottleneckAnalysis:
        """Analyze a system build for complexity and bottlenecks"""
        system_metadata = self.system_lifecycle.systems_catalog.get(system_id)
        if not system_metadata:
            raise ValueError(f"System {system_id} not found")
            
        # Analyze system requirements and current state
        requirements = system_metadata.get("requirements", {})
        current_stage = system_metadata.get("stage", "planning")
        
        # Identify potential bottlenecks
        bottlenecks = self._identify_bottlenecks(requirements, current_stage)
        
        # Break down into modules
        modules = self._create_build_modules(bottlenecks, requirements)
        
        # Calculate optimization potential
        total_sequential_time = sum(m.estimated_duration for m in modules)
        parallel_time = self._calculate_parallel_time(modules)
        time_saved = total_sequential_time - parallel_time
        
        # Determine execution mode
        recommended_mode = self._determine_execution_mode(modules, time_saved)
        
        return BottleneckAnalysis(
            bottleneck_id=str(uuid.uuid4()),
            type=self._classify_bottleneck_type(requirements),
            description=f"Complex build optimization for {system_metadata.get('name', 'Unknown System')}",
            complexity=self._assess_complexity(modules),
            estimated_impact=time_saved,
            modules=modules,
            recommended_mode=recommended_mode,
            optimization_strategy=self._generate_optimization_strategy(modules, recommended_mode),
            parallelization_potential=time_saved / total_sequential_time if total_sequential_time > 0 else 0.0
        )
    
    def start_fastpath_optimization(self, system_id: str, config: FastPathConfig = None) -> str:
        """Start FastPath optimization for a system"""
        if config is None:
            config = FastPathConfig()
            
        # Analyze the build
        analysis = self.analyze_build_complexity(system_id)
        
        # Only optimize if complexity threshold is met
        if analysis.complexity.value < config.complexity_threshold.value:
            return f"Build complexity ({analysis.complexity.value}) below threshold ({config.complexity_threshold.value})"
        
        optimization_id = str(uuid.uuid4())
        
        # Create optimization session
        self.active_optimizations[optimization_id] = {
            "system_id": system_id,
            "analysis": analysis,
            "config": config,
            "status": "running",
            "start_time": datetime.now(),
            "completed_modules": [],
            "failed_modules": [],
            "current_modules": [],
            "threads": {}
        }
        
        # Start optimization in background thread
        thread = threading.Thread(
            target=self._run_optimization,
            args=(optimization_id,),
            daemon=True
        )
        thread.start()
        self.active_optimizations[optimization_id]["threads"]["main"] = thread
        
        # Log the optimization start
        self.memory_system.log_event("fastpath_optimization_started", {
            "optimization_id": optimization_id,
            "system_id": system_id,
            "analysis": self._serialize_analysis(analysis),
            "config": asdict(config)
        })
        
        return optimization_id
    
    def get_optimization_status(self, optimization_id: str) -> Dict[str, Any]:
        """Get the current status of a FastPath optimization"""
        if optimization_id not in self.active_optimizations:
            return {"error": "Optimization not found"}
            
        opt = self.active_optimizations[optimization_id]
        analysis = opt["analysis"]
        
        # Calculate progress
        total_modules = len(analysis.modules)
        completed = len(opt["completed_modules"])
        failed = len(opt["failed_modules"])
        running = len(opt["current_modules"])
        
        progress = {
            "total_modules": total_modules,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": total_modules - completed - failed - running,
            "completion_percentage": (completed / total_modules * 100) if total_modules > 0 else 0
        }
        
        return {
            "optimization_id": optimization_id,
            "system_id": opt["system_id"],
            "status": opt["status"],
            "start_time": opt["start_time"].isoformat(),
            "progress": progress,
            "estimated_impact": analysis.estimated_impact,
            "parallelization_potential": analysis.parallelization_potential,
            "recommended_mode": analysis.recommended_mode.value,
            "completed_modules": opt["completed_modules"],
            "failed_modules": opt["failed_modules"],
            "current_modules": opt["current_modules"]
        }
    
    def pause_optimization(self, optimization_id: str) -> bool:
        """Pause a running optimization"""
        if optimization_id not in self.active_optimizations:
            return False
            
        opt = self.active_optimizations[optimization_id]
        if opt["status"] == "running":
            opt["status"] = "paused"
            self.memory_system.log_event("fastpath_optimization_paused", {
                "optimization_id": optimization_id
            })
            return True
        return False
    
    def resume_optimization(self, optimization_id: str) -> bool:
        """Resume a paused optimization"""
        if optimization_id not in self.active_optimizations:
            return False
            
        opt = self.active_optimizations[optimization_id]
        if opt["status"] == "paused":
            opt["status"] = "running"
            
            # Restart optimization thread
            thread = threading.Thread(
                target=self._run_optimization,
                args=(optimization_id,),
                daemon=True
            )
            thread.start()
            opt["threads"]["main"] = thread
            
            self.memory_system.log_event("fastpath_optimization_resumed", {
                "optimization_id": optimization_id
            })
            return True
        return False
    
    def stop_optimization(self, optimization_id: str) -> bool:
        """Stop a running optimization"""
        if optimization_id not in self.active_optimizations:
            return False
            
        opt = self.active_optimizations[optimization_id]
        opt["status"] = "stopped"
        
        # Clean up threads
        for thread in opt["threads"].values():
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        self.memory_system.log_event("fastpath_optimization_stopped", {
            "optimization_id": optimization_id
        })
        
        return True
    
    def _run_optimization(self, optimization_id: str):
        """Main optimization execution loop"""
        opt = self.active_optimizations[optimization_id]
        analysis = opt["analysis"]
        config = opt["config"]
        
        try:
            # Sort modules by priority and dependencies
            sorted_modules = self._sort_modules_by_dependencies(analysis.modules)
            
            # Execute modules based on recommended mode
            if analysis.recommended_mode == ExecutionMode.PARALLEL:
                self._execute_parallel_modules(sorted_modules, optimization_id, config)
            elif analysis.recommended_mode == ExecutionMode.PIPELINE:
                self._execute_pipeline_modules(sorted_modules, optimization_id, config)
            else:
                self._execute_sequential_modules(sorted_modules, optimization_id, config)
                
            # Mark optimization as complete
            opt["status"] = "completed"
            opt["end_time"] = datetime.now()
            
            self.memory_system.log_event("fastpath_optimization_completed", {
                "optimization_id": optimization_id,
                "duration": (opt["end_time"] - opt["start_time"]).total_seconds(),
                "modules_completed": len(opt["completed_modules"]),
                "time_saved": analysis.estimated_impact
            })
            
        except Exception as e:
            opt["status"] = "failed"
            opt["error"] = str(e)
            
            self.memory_system.log_event("fastpath_optimization_failed", {
                "optimization_id": optimization_id,
                "error": str(e)
            })
    
    def _execute_parallel_modules(self, modules: List[BuildModule], optimization_id: str, config: FastPathConfig):
        """Execute modules in parallel"""
        opt = self.active_optimizations[optimization_id]
        
        # Group modules by dependency level
        dependency_groups = self._group_by_dependencies(modules)
        
        for group in dependency_groups:
            if opt["status"] != "running":
                break
                
            # Start parallel execution for this group
            threads = []
            for module in group[:config.max_parallel_modules]:
                thread = threading.Thread(
                    target=self._execute_module,
                    args=(module, optimization_id),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
                opt["current_modules"].append(module.module_id)
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
    
    def _execute_pipeline_modules(self, modules: List[BuildModule], optimization_id: str, config: FastPathConfig):
        """Execute modules in pipeline mode"""
        opt = self.active_optimizations[optimization_id]
        
        # Create pipeline stages
        pipeline_stages = self._create_pipeline_stages(modules)
        
        for stage in pipeline_stages:
            if opt["status"] != "running":
                break
                
            # Execute stage in parallel
            threads = []
            for module in stage:
                thread = threading.Thread(
                    target=self._execute_module,
                    args=(module, optimization_id),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
                opt["current_modules"].append(module.module_id)
            
            # Wait for stage completion
            for thread in threads:
                thread.join()
    
    def _execute_sequential_modules(self, modules: List[BuildModule], optimization_id: str, config: FastPathConfig):
        """Execute modules sequentially"""
        opt = self.active_optimizations[optimization_id]
        
        for module in modules:
            if opt["status"] != "running":
                break
                
            self._execute_module(module, optimization_id)
    
    def _execute_module(self, module: BuildModule, optimization_id: str):
        """Execute a single module"""
        opt = self.active_optimizations[optimization_id]
        
        try:
            module.start_time = datetime.now()
            module.status = "running"
            
            # Assign agent if not already assigned
            if not module.assigned_agent:
                module.assigned_agent = self._select_agent_for_module(module)
            
            # Create task for the agent
            task_id = self.agent_orchestrator.create_task(
                title=f"FastPath: {module.name}",
                description=module.description,
                priority=module.priority,
                context={
                    "module_id": module.module_id,
                    "optimization_id": optimization_id,
                    "complexity": module.complexity.value,
                    "estimated_duration": module.estimated_duration
                }
            )
            
            # Route task to assigned agent
            self.agent_orchestrator.route_task(task_id)
            
            # Simulate module execution (in real implementation, this would wait for task completion)
            time.sleep(module.estimated_duration * 0.1)  # 10% of estimated time for demo
            
            module.end_time = datetime.now()
            module.status = "completed"
            
            # Update optimization state
            opt["completed_modules"].append(module.module_id)
            if module.module_id in opt["current_modules"]:
                opt["current_modules"].remove(module.module_id)
            
            self.memory_system.log_event("fastpath_module_completed", {
                "optimization_id": optimization_id,
                "module_id": module.module_id,
                "module_name": module.name,
                "duration": (module.end_time - module.start_time).total_seconds(),
                "assigned_agent": module.assigned_agent
            })
            
        except Exception as e:
            module.status = "failed"
            opt["failed_modules"].append(module.module_id)
            if module.module_id in opt["current_modules"]:
                opt["current_modules"].remove(module.module_id)
            
            self.memory_system.log_event("fastpath_module_failed", {
                "optimization_id": optimization_id,
                "module_id": module.module_id,
                "module_name": module.name,
                "error": str(e)
            })
    
    def _identify_bottlenecks(self, requirements: Dict[str, Any], current_stage: str) -> List[Dict[str, Any]]:
        """Identify potential bottlenecks in the build"""
        bottlenecks = []
        
        # Check for common bottleneck patterns
        for pattern in self.bottleneck_patterns:
            if self._matches_pattern(requirements, pattern):
                bottlenecks.append(pattern)
        
        # Add stage-specific bottlenecks
        if current_stage == "planning":
            bottlenecks.append({
                "type": "integration",
                "description": "Complex system architecture planning",
                "complexity": "moderate"
            })
        elif current_stage == "build":
            if "ai_models" in requirements:
                bottlenecks.append({
                    "type": "ai_model",
                    "description": "AI model integration and training",
                    "complexity": "complex"
                })
            if "third_party_apis" in requirements:
                bottlenecks.append({
                    "type": "third_party_api",
                    "description": "Third-party API integration",
                    "complexity": "moderate"
                })
        
        return bottlenecks
    
    def _create_build_modules(self, bottlenecks: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[BuildModule]:
        """Create build modules from bottlenecks and requirements"""
        modules = []
        
        for bottleneck in bottlenecks:
            # Create modules based on bottleneck type
            if bottleneck["type"] == "ai_model":
                modules.extend(self._create_ai_model_modules(requirements))
            elif bottleneck["type"] == "integration":
                modules.extend(self._create_integration_modules(requirements))
            elif bottleneck["type"] == "third_party_api":
                modules.extend(self._create_api_modules(requirements))
            else:
                # Generic module creation
                modules.append(BuildModule(
                    module_id=str(uuid.uuid4()),
                    name=f"Resolve {bottleneck['type']} bottleneck",
                    description=bottleneck["description"],
                    complexity=ComplexityLevel(bottleneck["complexity"]),
                    estimated_duration=60,  # Default 1 hour
                    dependencies=[],
                    required_agents=["Builder"],
                    parallelizable=True,
                    priority=8
                ))
        
        return modules
    
    def _create_ai_model_modules(self, requirements: Dict[str, Any]) -> List[BuildModule]:
        """Create modules for AI model integration"""
        modules = []
        
        # Model selection and setup
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="AI Model Selection & Setup",
            description="Select and configure AI models for the system",
            complexity=ComplexityLevel.COMPLEX,
            estimated_duration=120,
            dependencies=[],
            required_agents=["AI Agent"],
            parallelizable=False,
            priority=9
        ))
        
        # Model training/fine-tuning
        if "custom_training" in requirements:
            modules.append(BuildModule(
                module_id=str(uuid.uuid4()),
                name="Model Training & Fine-tuning",
                description="Train and fine-tune AI models on custom data",
                complexity=ComplexityLevel.ENTERPRISE,
                estimated_duration=240,
                dependencies=["AI Model Selection & Setup"],
                required_agents=["AI Agent", "Data Agent"],
                parallelizable=True,
                priority=10
            ))
        
        # API integration
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="AI API Integration",
            description="Integrate AI models into the application API",
            complexity=ComplexityLevel.MODERATE,
            estimated_duration=90,
            dependencies=["AI Model Selection & Setup"],
            required_agents=["Builder", "AI Agent"],
            parallelizable=True,
            priority=7
        ))
        
        return modules
    
    def _create_integration_modules(self, requirements: Dict[str, Any]) -> List[BuildModule]:
        """Create modules for system integration"""
        modules = []
        
        # Frontend integration
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="Frontend Integration",
            description="Integrate frontend components and UI",
            complexity=ComplexityLevel.MODERATE,
            estimated_duration=60,
            dependencies=[],
            required_agents=["UI Agent"],
            parallelizable=True,
            priority=6
        ))
        
        # Backend integration
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="Backend Integration",
            description="Integrate backend services and APIs",
            complexity=ComplexityLevel.MODERATE,
            estimated_duration=90,
            dependencies=[],
            required_agents=["Builder"],
            parallelizable=True,
            priority=7
        ))
        
        # Database integration
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="Database Integration",
            description="Set up and integrate database systems",
            complexity=ComplexityLevel.MODERATE,
            estimated_duration=45,
            dependencies=[],
            required_agents=["Infra Agent"],
            parallelizable=True,
            priority=5
        ))
        
        return modules
    
    def _create_api_modules(self, requirements: Dict[str, Any]) -> List[BuildModule]:
        """Create modules for third-party API integration"""
        modules = []
        
        # API research and selection
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="API Research & Selection",
            description="Research and select appropriate third-party APIs",
            complexity=ComplexityLevel.SIMPLE,
            estimated_duration=30,
            dependencies=[],
            required_agents=["Research Agent"],
            parallelizable=True,
            priority=4
        ))
        
        # API integration
        modules.append(BuildModule(
            module_id=str(uuid.uuid4()),
            name="API Integration",
            description="Integrate selected third-party APIs",
            complexity=ComplexityLevel.MODERATE,
            estimated_duration=75,
            dependencies=["API Research & Selection"],
            required_agents=["Builder"],
            parallelizable=True,
            priority=6
        ))
        
        return modules
    
    def _calculate_parallel_time(self, modules: List[BuildModule]) -> int:
        """Calculate total time if modules are executed in parallel"""
        if not modules:
            return 0
        
        # Group by dependencies and calculate max time per group
        dependency_groups = self._group_by_dependencies(modules)
        total_time = 0
        
        for group in dependency_groups:
            group_time = max(m.estimated_duration for m in group)
            total_time += group_time
        
        return total_time
    
    def _determine_execution_mode(self, modules: List[BuildModule], time_saved: int) -> ExecutionMode:
        """Determine the best execution mode based on modules and optimization potential"""
        if time_saved > 120:  # More than 2 hours saved
            return ExecutionMode.PARALLEL
        elif time_saved > 60:  # More than 1 hour saved
            return ExecutionMode.PIPELINE
        else:
            return ExecutionMode.SEQUENTIAL
    
    def _sort_modules_by_dependencies(self, modules: List[BuildModule]) -> List[BuildModule]:
        """Sort modules by dependencies (topological sort)"""
        # Simple dependency sorting - in production, use proper topological sort
        return sorted(modules, key=lambda m: (len(m.dependencies), -m.priority))
    
    def _group_by_dependencies(self, modules: List[BuildModule]) -> List[List[BuildModule]]:
        """Group modules by dependency level"""
        groups = []
        remaining = modules.copy()
        
        while remaining:
            # Find modules with no dependencies or all dependencies satisfied
            current_group = []
            for module in remaining[:]:
                if not module.dependencies or all(dep in [m.module_id for m in current_group] for dep in module.dependencies):
                    current_group.append(module)
                    remaining.remove(module)
            
            if current_group:
                groups.append(current_group)
            else:
                # Handle circular dependencies by adding remaining modules
                groups.append(remaining)
                break
        
        return groups
    
    def _create_pipeline_stages(self, modules: List[BuildModule]) -> List[List[BuildModule]]:
        """Create pipeline stages for pipeline execution mode"""
        return self._group_by_dependencies(modules)
    
    def _select_agent_for_module(self, module: BuildModule) -> str:
        """Select the best agent for a module"""
        available_agents = self.agent_orchestrator.get_agent_states()
        
        # Find agents that can handle this module
        suitable_agents = []
        for agent_id, agent_state in available_agents.items():
            if any(req_agent in agent_id.lower() for req_agent in module.required_agents):
                suitable_agents.append((agent_id, agent_state))
        
        if suitable_agents:
            # Select agent with lowest current load
            return min(suitable_agents, key=lambda x: x[1].get("current_tasks", 0))[0]
        else:
            # Fallback to any available agent
            return list(available_agents.keys())[0] if available_agents else "Builder"
    
    def _assess_complexity(self, modules: List[BuildModule]) -> ComplexityLevel:
        """Assess overall complexity based on modules"""
        if not modules:
            return ComplexityLevel.SIMPLE
        
        avg_complexity = sum(m.complexity.value for m in modules) / len(modules)
        
        if avg_complexity >= 3:
            return ComplexityLevel.ENTERPRISE
        elif avg_complexity >= 2:
            return ComplexityLevel.COMPLEX
        elif avg_complexity >= 1:
            return ComplexityLevel.MODERATE
        else:
            return ComplexityLevel.SIMPLE
    
    def _classify_bottleneck_type(self, requirements: Dict[str, Any]) -> BottleneckType:
        """Classify the type of bottleneck based on requirements"""
        if "ai_models" in requirements:
            return BottleneckType.AI_MODEL
        elif "third_party_apis" in requirements:
            return BottleneckType.THIRD_PARTY_API
        elif "complex_ui" in requirements:
            return BottleneckType.UI_COMPLEXITY
        elif "data_processing" in requirements:
            return BottleneckType.DATA_PROCESSING
        else:
            return BottleneckType.INTEGRATION
    
    def _generate_optimization_strategy(self, modules: List[BuildModule], mode: ExecutionMode) -> str:
        """Generate optimization strategy description"""
        if mode == ExecutionMode.PARALLEL:
            return f"Execute {len(modules)} modules in parallel with dependency-aware grouping"
        elif mode == ExecutionMode.PIPELINE:
            return f"Execute modules in pipeline stages for optimal resource utilization"
        else:
            return f"Execute {len(modules)} modules sequentially with priority ordering"
    
    def _matches_pattern(self, requirements: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
        """Check if requirements match a bottleneck pattern"""
        # Simple pattern matching - in production, use more sophisticated matching
        pattern_keywords = pattern.get("keywords", [])
        for keyword in pattern_keywords:
            if keyword.lower() in str(requirements).lower():
                return True
        return False
    
    def _serialize_analysis(self, analysis: BottleneckAnalysis) -> Dict[str, Any]:
        """Serialize analysis for JSON storage"""
        return {
            "bottleneck_id": analysis.bottleneck_id,
            "type": analysis.type.value,
            "description": analysis.description,
            "complexity": analysis.complexity.value,
            "estimated_impact": analysis.estimated_impact,
            "modules": [asdict(m) for m in analysis.modules],
            "recommended_mode": analysis.recommended_mode.value,
            "optimization_strategy": analysis.optimization_strategy,
            "parallelization_potential": analysis.parallelization_potential
        }
    
    def _load_module_templates(self) -> Dict[str, Any]:
        """Load module templates from configuration"""
        # In production, load from file or database
        return {
            "ai_model": {
                "selection": {"duration": 120, "agents": ["AI Agent"]},
                "training": {"duration": 240, "agents": ["AI Agent", "Data Agent"]},
                "integration": {"duration": 90, "agents": ["Builder", "AI Agent"]}
            },
            "integration": {
                "frontend": {"duration": 60, "agents": ["UI Agent"]},
                "backend": {"duration": 90, "agents": ["Builder"]},
                "database": {"duration": 45, "agents": ["Infra Agent"]}
            }
        }
    
    def _load_bottleneck_patterns(self) -> List[Dict[str, Any]]:
        """Load bottleneck patterns from configuration"""
        # In production, load from file or database
        return [
            {
                "type": "ai_model",
                "keywords": ["ai", "machine learning", "neural network", "model"],
                "complexity": "complex"
            },
            {
                "type": "third_party_api",
                "keywords": ["api", "integration", "third party", "external"],
                "complexity": "moderate"
            },
            {
                "type": "ui_complexity",
                "keywords": ["complex ui", "advanced interface", "real-time", "interactive"],
                "complexity": "moderate"
            }
        ]
