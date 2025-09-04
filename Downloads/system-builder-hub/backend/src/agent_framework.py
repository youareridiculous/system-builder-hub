"""
🧠 System Build Hub OS - Multi-Agent Orchestration Framework

This module provides the foundation for the multi-agent mesh system
that powers the System Build Hub OS.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Agent roles and capabilities
class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    BUILDER = "builder"
    UI_AGENT = "ui_agent"
    INFRA_AGENT = "infra_agent"
    MEMORY_AGENT = "memory_agent"
    SYNTHESIZER = "synthesizer"
    PROMPTER = "prompter"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    name: str
    description: str
    supported_tasks: List[str]
    memory_access_level: str  # "read", "write", "full"
    llm_models: List[str]  # Which LLMs this agent can use

@dataclass
class Task:
    """Represents a task in the system"""
    id: str
    title: str
    description: str
    assigned_agent: Optional[str]
    status: TaskStatus
    priority: int  # 1-10, higher = more important
    created_at: datetime
    updated_at: datetime
    dependencies: List[str]  # Task IDs this depends on
    context: Dict[str, Any]  # Task-specific context
    memory_references: List[str]  # Memory session IDs

@dataclass
class Agent:
    """Represents an AI agent in the system"""
    id: str
    role: AgentRole
    name: str
    description: str
    capabilities: List[AgentCapability]
    memory_access: List[str]  # Memory session IDs this agent can access
    task_boundaries: List[str]  # What types of tasks this agent can handle
    current_tasks: List[str]  # Task IDs currently assigned
    status: str  # "available", "busy", "offline"
    created_at: datetime
    last_active: datetime

class MemorySystem:
    """Memory management system for agents"""
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = memory_dir
        self.sessions = {}
    
    def initialize(self):
        """Initialize the memory system"""
        pass
    
    def save_state(self):
        """Save memory system state"""
        pass
    
    def cleanup_old_sessions(self):
        """Clean up old memory sessions"""
        return {"cleaned": 0}
    
    def ingest_file(self, filepath: str, session_id: str):
        """Ingest file into memory"""
        return {"status": "ingested", "session_id": session_id}


class AgentOrchestrator:
    """
    Core orchestrator that routes tasks and coordinates agents
    """
    
    def __init__(self, memory_system=None):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.memory_system = memory_system
        self.task_queue: List[str] = []
        self.active_tasks: Dict[str, str] = {}  # task_id -> agent_id
        
        # Initialize default agents
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize the core agent set"""
        
        # Orchestrator Agent
        orchestrator = Agent(
            id="orchestrator-001",
            role=AgentRole.ORCHESTRATOR,
            name="System Orchestrator",
            description="Coordinates all other agents and routes tasks intelligently",
            capabilities=[
                AgentCapability(
                    name="task_routing",
                    description="Routes tasks to appropriate agents based on content and context",
                    supported_tasks=["route_task", "resolve_conflicts", "coordinate_agents"],
                    memory_access_level="full",
                    llm_models=["gpt-4", "claude-3", "gemini-pro"]
                )
            ],
            memory_access=["*"],  # Can access all memory
            task_boundaries=["orchestration", "coordination", "routing"],
            current_tasks=[],
            status="available",
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        # Builder Agent
        builder = Agent(
            id="builder-001",
            role=AgentRole.BUILDER,
            name="Code Builder",
            description="Writes code, generates templates, and handles technical specifications",
            capabilities=[
                AgentCapability(
                    name="code_generation",
                    description="Generates code based on specifications and requirements",
                    supported_tasks=["write_code", "generate_templates", "refactor_code"],
                    memory_access_level="read",
                    llm_models=["gpt-4", "claude-3", "gemini-pro"]
                )
            ],
            memory_access=["code_patterns", "templates", "best_practices"],
            task_boundaries=["coding", "templating", "refactoring"],
            current_tasks=[],
            status="available",
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        # Memory Agent
        memory_agent = Agent(
            id="memory-001",
            role=AgentRole.MEMORY_AGENT,
            name="Memory Manager",
            description="Logs all builds, errors, lessons, and decisions",
            capabilities=[
                AgentCapability(
                    name="memory_logging",
                    description="Logs and organizes project memory and lessons learned",
                    supported_tasks=["log_build", "log_error", "log_decision", "organize_memory"],
                    memory_access_level="write",
                    llm_models=["gpt-4", "claude-3"]
                )
            ],
            memory_access=["*"],
            task_boundaries=["logging", "memory_management", "knowledge_extraction"],
            current_tasks=[],
            status="available",
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        self.agents[orchestrator.id] = orchestrator
        self.agents[builder.id] = builder
        self.agents[memory_agent.id] = memory_agent
    
    def create_task(self, title: str, description: str, priority: int = 5, 
                   dependencies: List[str] = None, context: Dict[str, Any] = None) -> str:
        """Create a new task in the system"""
        
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            assigned_agent=None,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            dependencies=dependencies or [],
            context=context or {},
            memory_references=[]
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        # Log task creation
        if self.memory_system:
            self.memory_system.log_event("task_created", {
                "task_id": task_id,
                "title": title,
                "priority": priority
            })
        
        return task_id
    
    def route_task(self, task_id: str) -> Optional[str]:
        """
        Route a task to the most appropriate agent using AI-powered decision making
        """
        
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        
        # Simple routing logic (will be enhanced with LLM)
        best_agent = None
        best_score = 0
        
        for agent_id, agent in self.agents.items():
            if agent.status != "available":
                continue
            
            # Calculate agent suitability score
            score = self._calculate_agent_suitability(agent, task)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        if best_agent:
            # Assign task to agent
            task.assigned_agent = best_agent
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.now()
            
            self.agents[best_agent].current_tasks.append(task_id)
            self.active_tasks[task_id] = best_agent
            
            # Remove from queue
            if task_id in self.task_queue:
                self.task_queue.remove(task_id)
            
            # Log task assignment
            if self.memory_system:
                self.memory_system.log_event("task_assigned", {
                    "task_id": task_id,
                    "agent_id": best_agent,
                    "score": best_score
                })
            
            return best_agent
        
        return None
    
    def _calculate_agent_suitability(self, agent: Agent, task: Task) -> float:
        """
        Calculate how suitable an agent is for a given task
        This is a simple implementation - will be enhanced with LLM reasoning
        """
        
        score = 0.0
        
        # Check if agent can handle this type of task
        task_keywords = task.title.lower().split() + task.description.lower().split()
        
        for boundary in agent.task_boundaries:
            if boundary.lower() in task_keywords:
                score += 0.3
        
        # Check agent availability
        if agent.status == "available":
            score += 0.2
        
        # Check current workload
        workload_factor = 1.0 / (len(agent.current_tasks) + 1)
        score += workload_factor * 0.2
        
        # Check memory access compatibility
        if task.memory_references:
            accessible_memory = 0
            for memory_ref in task.memory_references:
                if memory_ref in agent.memory_access or "*" in agent.memory_access:
                    accessible_memory += 1
            
            memory_score = accessible_memory / len(task.memory_references)
            score += memory_score * 0.3
        
        return min(score, 1.0)
    
    def complete_task(self, task_id: str, result: Dict[str, Any] = None) -> bool:
        """Mark a task as completed"""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now()
        
        # Remove from active tasks
        if task_id in self.active_tasks:
            agent_id = self.active_tasks[task_id]
            if agent_id in self.agents:
                if task_id in self.agents[agent_id].current_tasks:
                    self.agents[agent_id].current_tasks.remove(task_id)
            del self.active_tasks[task_id]
        
        # Log completion
        if self.memory_system:
            self.memory_system.log_event("task_completed", {
                "task_id": task_id,
                "result": result or {},
                "duration": (task.updated_at - task.created_at).total_seconds()
            })
        
        return True
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        
        return {
            "total_agents": len(self.agents),
            "available_agents": len([a for a in self.agents.values() if a.status == "available"]),
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            "queue_length": len(self.task_queue)
        }
    
    def add_agent(self, agent: Agent) -> str:
        """Add a new agent to the system"""
        
        self.agents[agent.id] = agent
        
        # Log agent addition
        if self.memory_system:
            self.memory_system.log_event("agent_added", {
                "agent_id": agent.id,
                "role": agent.role.value,
                "name": agent.name
            })
        
        return agent.id
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the system"""
        
        if agent_id not in self.agents:
            return False
        
        # Reassign any active tasks
        agent = self.agents[agent_id]
        for task_id in agent.current_tasks[:]:  # Copy list to avoid modification during iteration
            self._reassign_task(task_id)
        
        del self.agents[agent_id]
        
        # Log agent removal
        if self.memory_system:
            self.memory_system.log_event("agent_removed", {
                "agent_id": agent_id
            })
        
        return True
    
    def _reassign_task(self, task_id: str) -> bool:
        """Reassign a task to a different agent"""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.assigned_agent = None
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.now()
        
        # Add back to queue
        if task_id not in self.task_queue:
            self.task_queue.append(task_id)
        
        # Remove from active tasks
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        return True
    
    def create_task(self, title: str, description: str, priority: int = 5,
                   dependencies: List[str] = None, context: Dict[str, Any] = None) -> str:
        """Create a new task"""
        
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            assigned_agent=None,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            dependencies=dependencies or [],
            context=context or {},
            memory_references=[]
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        # Log task creation
        if self.memory_system:
            self.memory_system.log_event("task_created", {
                "task_id": task_id,
                "title": title,
                "priority": priority
            })
        
        return task_id
    
    def create_and_route_task(self, task_data: Dict[str, Any]) -> str:
        """Create a task and route it to an agent"""
        
        task_id = self.create_task(
            title=task_data.get("title", "Untitled Task"),
            description=task_data.get("description", ""),
            priority=task_data.get("priority", 5),
            dependencies=task_data.get("dependencies", []),
            context=task_data.get("context", {})
        )
        
        # Route the task
        assigned_agent = self.route_task(task_id)
        
        return task_id
    
    def route_task(self, task_id: str) -> Optional[str]:
        """Route a task to an appropriate agent"""
        
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        # Find best available agent
        best_agent = None
        best_score = 0
        
        for agent_id, agent in self.agents.items():
            if agent.status != "available":
                continue
            
            # Simple scoring based on role and current load
            score = 10 - len(agent.current_tasks)  # Prefer less busy agents
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        if best_agent:
            # Assign task to agent
            task.assigned_agent = best_agent
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.now()
            
            agent = self.agents[best_agent]
            agent.current_tasks.append(task_id)
            agent.last_active = datetime.now()
            
            # Move from queue to active
            if task_id in self.task_queue:
                self.task_queue.remove(task_id)
            self.active_tasks[task_id] = best_agent
            
            # Log task assignment
            if self.memory_system:
                self.memory_system.log_event("task_assigned", {
                    "task_id": task_id,
                    "agent_id": best_agent,
                    "agent_role": agent.role.value
                })
            
            return best_agent
        
        return None
    
    def get_agent_states(self) -> Dict[str, Any]:
        """Get current state of all agents"""
        states = {}
        for agent_id, agent in self.agents.items():
            states[agent_id] = {
                "id": agent.id,
                "role": agent.role.value,
                "name": agent.name,
                "status": agent.status,
                "current_tasks": agent.current_tasks,
                "last_active": agent.last_active.isoformat()
            }
        return states
    
    def restore_agent_states(self, states: Dict[str, Any]):
        """Restore agent states from checkpoint"""
        # This is a simplified implementation
        # In a real system, you'd want more sophisticated state restoration
        for agent_id, state in states.items():
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.status = state.get("status", "available")
                agent.current_tasks = state.get("current_tasks", [])


