"""
🔄 System Build Hub OS - Autonomous Builder

This module enables autonomous build loops with continuous improvement,
goal-driven development, and checkpoint management.
"""

import json
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from system_lifecycle import SystemLifecycleManager, SystemStage, SystemStatus
from agent_framework import AgentOrchestrator, MemorySystem
from project_loader import ProjectLoader, BuildPhase

class LoopStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class GoalType(Enum):
    COMPLETION = "completion"
    OPTIMIZATION = "optimization"
    FEATURE_ADDITION = "feature_addition"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    DEPLOYMENT = "deployment"

@dataclass
class BuildGoal:
    """Goal for autonomous build loop"""
    id: str
    system_id: str
    goal_type: GoalType
    description: str
    success_criteria: List[str]
    priority: int  # 1-10
    created_at: datetime
    target_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class LoopConfig:
    """Configuration for autonomous build loop"""
    system_id: str
    goals: List[BuildGoal]
    max_iterations: int = 100
    iteration_timeout: int = 300  # seconds
    checkpoint_interval: int = 10  # iterations
    auto_pause_on_error: bool = True
    enable_rollback: bool = True
    notification_callbacks: List[Callable] = None

@dataclass
class Checkpoint:
    """Checkpoint for rollback and recovery"""
    id: str
    system_id: str
    iteration: int
    timestamp: datetime
    system_state: Dict[str, Any]
    agent_states: Dict[str, Any]
    memory_snapshot: Dict[str, Any]
    goals_progress: Dict[str, float]
    metadata: Dict[str, Any]

@dataclass
class LoopProgress:
    """Progress tracking for autonomous build loop"""
    system_id: str
    current_iteration: int
    total_iterations: int
    status: LoopStatus
    start_time: datetime
    last_activity: datetime
    goals_completed: int
    total_goals: int
    current_goal: Optional[str]
    estimated_completion: Optional[datetime]
    checkpoints: List[str]
    errors: List[str]

class AutonomousBuilder:
    """
    Manages autonomous build loops with continuous improvement
    """
    
    def __init__(self, base_dir: Path, system_lifecycle: SystemLifecycleManager,
                 agent_orchestrator: AgentOrchestrator, memory_system: MemorySystem,
                 project_loader: ProjectLoader):
        self.base_dir = base_dir
        self.system_lifecycle = system_lifecycle
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.project_loader = project_loader
        
        # Active loops tracking
        self.active_loops: Dict[str, LoopConfig] = {}
        self.loop_progress: Dict[str, LoopProgress] = {}
        self.loop_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # Checkpoints and state management
        self.checkpoints_dir = base_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Load existing loops
        self._load_active_loops()
    
    def start_continuous_build(self, system_id: str, goals: List[Dict[str, Any]], 
                             config: Optional[Dict[str, Any]] = None) -> str:
        """
        Start autonomous build loop
        
        Args:
            system_id: ID of the system to build
            goals: List of goal definitions
            config: Optional configuration overrides
            
        Returns:
            Loop ID
        """
        try:
            # Validate system exists
            if system_id not in self.system_lifecycle.systems_catalog:
                raise ValueError(f"System {system_id} not found")
            
            # Create loop ID
            loop_id = f"loop-{uuid.uuid4().hex[:8]}"
            
            # Create build goals
            build_goals = []
            for goal_data in goals:
                goal = BuildGoal(
                    id=f"goal-{uuid.uuid4().hex[:8]}",
                    system_id=system_id,
                    goal_type=GoalType(goal_data.get("type", "completion")),
                    description=goal_data.get("description", ""),
                    success_criteria=goal_data.get("success_criteria", []),
                    priority=goal_data.get("priority", 5),
                    created_at=datetime.now(),
                    target_completion=goal_data.get("target_completion")
                )
                build_goals.append(goal)
            
            # Create loop configuration
            loop_config = LoopConfig(
                system_id=system_id,
                goals=build_goals,
                max_iterations=config.get("max_iterations", 100) if config else 100,
                iteration_timeout=config.get("iteration_timeout", 300) if config else 300,
                checkpoint_interval=config.get("checkpoint_interval", 10) if config else 10,
                auto_pause_on_error=config.get("auto_pause_on_error", True) if config else True,
                enable_rollback=config.get("enable_rollback", True) if config else True
            )
            
            # Create progress tracking
            progress = LoopProgress(
                system_id=system_id,
                current_iteration=0,
                total_iterations=loop_config.max_iterations,
                status=LoopStatus.RUNNING,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                goals_completed=0,
                total_goals=len(build_goals),
                current_goal=None,
                estimated_completion=None,
                checkpoints=[],
                errors=[]
            )
            
            # Store loop configuration
            self.active_loops[loop_id] = loop_config
            self.loop_progress[loop_id] = progress
            
            # Create stop event
            self.stop_events[loop_id] = threading.Event()
            
            # Start loop in background thread
            loop_thread = threading.Thread(
                target=self._run_build_loop,
                args=(loop_id,),
                daemon=True
            )
            self.loop_threads[loop_id] = loop_thread
            loop_thread.start()
            
            # Log loop start
            goals_data = []
            for goal in build_goals:
                goal_dict = asdict(goal)
                goal_dict['goal_type'] = goal.goal_type.value
                goal_dict['created_at'] = goal.created_at.isoformat()
                if goal.target_completion:
                    goal_dict['target_completion'] = goal.target_completion.isoformat()
                if goal.completed_at:
                    goal_dict['completed_at'] = goal.completed_at.isoformat()
                goals_data.append(goal_dict)
            
            config_dict = {
                "system_id": loop_config.system_id,
                "max_iterations": loop_config.max_iterations,
                "iteration_timeout": loop_config.iteration_timeout,
                "checkpoint_interval": loop_config.checkpoint_interval,
                "auto_pause_on_error": loop_config.auto_pause_on_error,
                "enable_rollback": loop_config.enable_rollback
            }
            
            self.memory_system.log_event("autonomous_loop_started", {
                "loop_id": loop_id,
                "system_id": system_id,
                "goals": goals_data,
                "config": config_dict
            })
            
            return loop_id
            
        except Exception as e:
            raise Exception(f"Failed to start continuous build: {str(e)}")
    
    def pause_loop(self, loop_id: str) -> bool:
        """
        Pause autonomous build loop
        
        Args:
            loop_id: ID of the loop to pause
            
        Returns:
            True if successful
        """
        try:
            if loop_id not in self.active_loops:
                raise ValueError(f"Loop {loop_id} not found")
            
            # Update progress status
            self.loop_progress[loop_id].status = LoopStatus.PAUSED
            self.loop_progress[loop_id].last_activity = datetime.now()
            
            # Log pause event
            self.memory_system.log_event("autonomous_loop_paused", {
                "loop_id": loop_id,
                "system_id": self.active_loops[loop_id].system_id,
                "iteration": self.loop_progress[loop_id].current_iteration
            })
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to pause loop: {str(e)}")
    
    def resume_loop(self, loop_id: str) -> bool:
        """
        Resume autonomous build loop
        
        Args:
            loop_id: ID of the loop to resume
            
        Returns:
            True if successful
        """
        try:
            if loop_id not in self.active_loops:
                raise ValueError(f"Loop {loop_id} not found")
            
            # Update progress status
            self.loop_progress[loop_id].status = LoopStatus.RUNNING
            self.loop_progress[loop_id].last_activity = datetime.now()
            
            # Log resume event
            self.memory_system.log_event("autonomous_loop_resumed", {
                "loop_id": loop_id,
                "system_id": self.active_loops[loop_id].system_id,
                "iteration": self.loop_progress[loop_id].current_iteration
            })
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to resume loop: {str(e)}")
    
    def stop_loop(self, loop_id: str) -> bool:
        """
        Stop autonomous build loop
        
        Args:
            loop_id: ID of the loop to stop
            
        Returns:
            True if successful
        """
        try:
            if loop_id not in self.active_loops:
                raise ValueError(f"Loop {loop_id} not found")
            
            # Set stop event
            self.stop_events[loop_id].set()
            
            # Update progress status
            self.loop_progress[loop_id].status = LoopStatus.STOPPED
            self.loop_progress[loop_id].last_activity = datetime.now()
            
            # Clean up
            self._cleanup_loop(loop_id)
            
            # Log stop event
            self.memory_system.log_event("autonomous_loop_stopped", {
                "loop_id": loop_id,
                "system_id": self.active_loops[loop_id].system_id,
                "final_iteration": self.loop_progress[loop_id].current_iteration
            })
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to stop loop: {str(e)}")
    
    def create_checkpoint(self, loop_id: str) -> str:
        """
        Create checkpoint for rollback
        
        Args:
            loop_id: ID of the loop
            
        Returns:
            Checkpoint ID
        """
        try:
            if loop_id not in self.active_loops:
                raise ValueError(f"Loop {loop_id} not found")
            
            loop_config = self.active_loops[loop_id]
            progress = self.loop_progress[loop_id]
            system_id = loop_config.system_id
            
            # Create checkpoint ID
            checkpoint_id = f"checkpoint-{uuid.uuid4().hex[:8]}"
            
            # Capture system state
            system_metadata = self.system_lifecycle.systems_catalog.get(system_id)
            system_dir = self.base_dir / "memory" / "systems" / system_id
            
            # Capture agent states
            agent_states = self.agent_orchestrator.get_agent_states()
            
            # Capture memory snapshot
            memory_snapshot = self.memory_system.get_system_memory(system_id)
            
            # Calculate goals progress
            goals_progress = {}
            for goal in loop_config.goals:
                progress_value = self._calculate_goal_progress(goal, system_metadata)
                goals_progress[goal.id] = progress_value
            
            # Create checkpoint
            checkpoint = Checkpoint(
                id=checkpoint_id,
                system_id=system_id,
                iteration=progress.current_iteration,
                timestamp=datetime.now(),
                system_state=asdict(system_metadata) if system_metadata else {},
                agent_states=agent_states,
                memory_snapshot=memory_snapshot,
                goals_progress=goals_progress,
                metadata={
                    "loop_id": loop_id,
                    "total_goals": len(loop_config.goals),
                    "goals_completed": progress.goals_completed
                }
            )
            
            # Save checkpoint
            self._save_checkpoint(checkpoint)
            
            # Update progress
            progress.checkpoints.append(checkpoint_id)
            
            # Log checkpoint creation
            self.memory_system.log_event("checkpoint_created", {
                "checkpoint_id": checkpoint_id,
                "loop_id": loop_id,
                "system_id": system_id,
                "iteration": progress.current_iteration
            })
            
            return checkpoint_id
            
        except Exception as e:
            raise Exception(f"Failed to create checkpoint: {str(e)}")
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback system to checkpoint
        
        Args:
            checkpoint_id: ID of the checkpoint to rollback to
            
        Returns:
            True if successful
        """
        try:
            # Load checkpoint
            checkpoint = self._load_checkpoint(checkpoint_id)
            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            
            system_id = checkpoint.system_id
            
            # Restore system state
            self.system_lifecycle.update_system_metadata(system_id, checkpoint.system_state)
            
            # Restore agent states
            self.agent_orchestrator.restore_agent_states(checkpoint.agent_states)
            
            # Restore memory snapshot
            self.memory_system.restore_system_memory(system_id, checkpoint.memory_snapshot)
            
            # Log rollback
            self.memory_system.log_event("rollback_executed", {
                "checkpoint_id": checkpoint_id,
                "system_id": system_id,
                "iteration": checkpoint.iteration,
                "timestamp": checkpoint.timestamp.isoformat()
            })
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to rollback to checkpoint: {str(e)}")
    
    def get_loop_status(self, loop_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of autonomous build loop
        
        Args:
            loop_id: ID of the loop
            
        Returns:
            Loop status information
        """
        try:
            if loop_id not in self.active_loops:
                return None
            
            loop_config = self.active_loops[loop_id]
            progress = self.loop_progress[loop_id]
            
            return {
                "loop_id": loop_id,
                "system_id": loop_config.system_id,
                "status": progress.status.value,
                "current_iteration": progress.current_iteration,
                "total_iterations": progress.total_iterations,
                "goals_completed": progress.goals_completed,
                "total_goals": progress.total_goals,
                "current_goal": progress.current_goal,
                "start_time": progress.start_time.isoformat(),
                "last_activity": progress.last_activity.isoformat(),
                "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                "checkpoints": progress.checkpoints,
                "errors": progress.errors
            }
            
        except Exception as e:
            raise Exception(f"Failed to get loop status: {str(e)}")
    
    def get_all_loops_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all active loops
        
        Returns:
            List of loop status information
        """
        try:
            status_list = []
            for loop_id in self.active_loops.keys():
                status = self.get_loop_status(loop_id)
                if status:
                    status_list.append(status)
            return status_list
            
        except Exception as e:
            raise Exception(f"Failed to get all loops status: {str(e)}")
    
    def _run_build_loop(self, loop_id: str):
        """Main loop execution function"""
        try:
            loop_config = self.active_loops[loop_id]
            progress = self.loop_progress[loop_id]
            stop_event = self.stop_events[loop_id]
            
            system_id = loop_config.system_id
            
            # Log loop start
            self.memory_system.log_event("build_loop_started", {
                "loop_id": loop_id,
                "system_id": system_id,
                "goals_count": len(loop_config.goals)
            })
            
            # Main loop
            while (progress.current_iteration < progress.total_iterations and 
                   progress.status == LoopStatus.RUNNING and 
                   not stop_event.is_set()):
                
                try:
                    # Update iteration
                    progress.current_iteration += 1
                    progress.last_activity = datetime.now()
                    
                    # Check if checkpoint needed
                    if progress.current_iteration % loop_config.checkpoint_interval == 0:
                        self.create_checkpoint(loop_id)
                    
                    # Execute iteration
                    self._execute_iteration(loop_id, progress.current_iteration)
                    
                    # Check goals completion
                    completed_goals = self._check_goals_completion(loop_config.goals, system_id)
                    progress.goals_completed = len(completed_goals)
                    
                    # Update current goal
                    current_goal = self._get_current_goal(loop_config.goals, system_id)
                    progress.current_goal = current_goal.id if current_goal else None
                    
                    # Check if all goals completed
                    if progress.goals_completed >= progress.total_goals:
                        progress.status = LoopStatus.COMPLETED
                        break
                    
                    # Sleep between iterations
                    time.sleep(1)
                    
                except Exception as e:
                    progress.errors.append(f"Iteration {progress.current_iteration}: {str(e)}")
                    
                    if loop_config.auto_pause_on_error:
                        progress.status = LoopStatus.PAUSED
                        break
                    
                    # Continue with next iteration
                    continue
            
            # Final checkpoint
            if progress.status == LoopStatus.COMPLETED:
                self.create_checkpoint(loop_id)
            
            # Update final status
            if progress.status == LoopStatus.RUNNING:
                progress.status = LoopStatus.COMPLETED
            
            # Log loop completion
            self.memory_system.log_event("build_loop_completed", {
                "loop_id": loop_id,
                "system_id": system_id,
                "final_iteration": progress.current_iteration,
                "goals_completed": progress.goals_completed,
                "status": progress.status.value
            })
            
        except Exception as e:
            # Handle loop failure
            if loop_id in self.loop_progress:
                self.loop_progress[loop_id].status = LoopStatus.FAILED
                self.loop_progress[loop_id].errors.append(f"Loop failure: {str(e)}")
            
            self.memory_system.log_event("build_loop_failed", {
                "loop_id": loop_id,
                "error": str(e)
            })
    
    def _execute_iteration(self, loop_id: str, iteration: int):
        """Execute a single iteration of the build loop"""
        try:
            loop_config = self.active_loops[loop_id]
            system_id = loop_config.system_id
            
            # Get current goal
            current_goal = self._get_current_goal(loop_config.goals, system_id)
            if not current_goal:
                return
            
            # Create task for current goal
            task_data = {
                "id": f"task-{uuid.uuid4().hex[:8]}",
                "title": f"Autonomous: {current_goal.description}",
                "description": f"Iteration {iteration} - {current_goal.description}",
                "priority": "high" if current_goal.priority >= 8 else "medium",
                "estimated_hours": 1,
                "dependencies": [],
                "assigned_agent": self._select_agent_for_goal(current_goal),
                "metadata": {
                    "loop_id": loop_id,
                    "iteration": iteration,
                    "goal_id": current_goal.id
                }
            }
            
            # Route task to agent
            task_result = self.agent_orchestrator.create_and_route_task(task_data)
            
            # Log iteration execution
            self.memory_system.log_event("iteration_executed", {
                "loop_id": loop_id,
                "system_id": system_id,
                "iteration": iteration,
                "goal_id": current_goal.id,
                "task_id": task_data["id"],
                "agent": task_data["assigned_agent"]
            })
            
        except Exception as e:
            raise Exception(f"Failed to execute iteration {iteration}: {str(e)}")
    
    def _get_current_goal(self, goals: List[BuildGoal], system_id: str) -> Optional[BuildGoal]:
        """Get the current active goal"""
        # Sort goals by priority and completion status
        active_goals = []
        for goal in goals:
            if not goal.completed_at:
                active_goals.append(goal)
        
        if not active_goals:
            return None
        
        # Return highest priority goal
        return max(active_goals, key=lambda g: g.priority)
    
    def _check_goals_completion(self, goals: List[BuildGoal], system_id: str) -> List[BuildGoal]:
        """Check which goals have been completed"""
        completed_goals = []
        system_metadata = self.system_lifecycle.systems_catalog.get(system_id)
        
        for goal in goals:
            if goal.completed_at:
                completed_goals.append(goal)
                continue
            
            # Check success criteria
            if self._evaluate_success_criteria(goal, system_metadata):
                goal.completed_at = datetime.now()
                completed_goals.append(goal)
        
        return completed_goals
    
    def _evaluate_success_criteria(self, goal: BuildGoal, system_metadata: Any) -> bool:
        """Evaluate if goal success criteria are met"""
        if not goal.success_criteria:
            return False
        
        # Simple evaluation - in a real implementation, this would be more sophisticated
        for criterion in goal.success_criteria:
            if "test" in criterion.lower() and system_metadata.current_stage != SystemStage.TEST:
                return False
            if "deploy" in criterion.lower() and system_metadata.current_stage != SystemStage.DEPLOY:
                return False
        
        return True
    
    def _calculate_goal_progress(self, goal: BuildGoal, system_metadata: Any) -> float:
        """Calculate progress percentage for a goal"""
        if goal.completed_at:
            return 100.0
        
        # Simple progress calculation based on system stage
        stage_progress = {
            SystemStage.IDEA: 10,
            SystemStage.PLAN: 25,
            SystemStage.BUILD: 50,
            SystemStage.TEST: 75,
            SystemStage.DEPLOY: 90,
            SystemStage.MAINTAIN: 100
        }
        
        return stage_progress.get(system_metadata.current_stage, 0)
    
    def _select_agent_for_goal(self, goal: BuildGoal) -> str:
        """Select appropriate agent for goal execution"""
        if goal.goal_type == GoalType.REFACTORING:
            return "refactorer"
        elif goal.goal_type == GoalType.DEPLOYMENT:
            return "infra"
        elif goal.goal_type == GoalType.BUG_FIX:
            return "builder"
        elif goal.goal_type == GoalType.FEATURE_ADDITION:
            return "builder"
        elif goal.goal_type == GoalType.OPTIMIZATION:
            return "synthesizer"
        else:
            return "builder"
    
    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save checkpoint to file"""
        checkpoint_file = self.checkpoints_dir / f"{checkpoint.id}.json"
        
        checkpoint_dict = asdict(checkpoint)
        checkpoint_dict["timestamp"] = checkpoint.timestamp.isoformat()
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_dict, f, indent=2)
    
    def _load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from file"""
        checkpoint_file = self.checkpoints_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct checkpoint object
            return Checkpoint(
                id=data["id"],
                system_id=data["system_id"],
                iteration=data["iteration"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                system_state=data["system_state"],
                agent_states=data["agent_states"],
                memory_snapshot=data["memory_snapshot"],
                goals_progress=data["goals_progress"],
                metadata=data["metadata"]
            )
        except Exception:
            return None
    
    def _cleanup_loop(self, loop_id: str):
        """Clean up loop resources"""
        if loop_id in self.active_loops:
            del self.active_loops[loop_id]
        if loop_id in self.loop_progress:
            del self.loop_progress[loop_id]
        if loop_id in self.loop_threads:
            del self.loop_threads[loop_id]
        if loop_id in self.stop_events:
            del self.stop_events[loop_id]
    
    def _load_active_loops(self):
        """Load active loops from persistent storage"""
        loops_file = self.base_dir / "active_loops.json"
        
        if loops_file.exists():
            try:
                with open(loops_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct active loops (simplified - in real implementation would be more complex)
                for loop_data in data.get("loops", []):
                    loop_id = loop_data["loop_id"]
                    # Note: In a real implementation, you'd reconstruct the full loop state
                    # For now, we'll just mark them as stopped
                    pass
                    
            except Exception as e:
                print(f"Failed to load active loops: {e}")
    
    def _save_active_loops(self):
        """Save active loops to persistent storage"""
        loops_file = self.base_dir / "active_loops.json"
        
        try:
            data = {
                "loops": [],
                "last_updated": datetime.now().isoformat()
            }
            
            for loop_id, loop_config in self.active_loops.items():
                progress = self.loop_progress.get(loop_id)
                if progress:
                    loop_data = {
                        "loop_id": loop_id,
                        "system_id": loop_config.system_id,
                        "status": progress.status.value,
                        "current_iteration": progress.current_iteration,
                        "goals_completed": progress.goals_completed
                    }
                    data["loops"].append(loop_data)
            
            with open(loops_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save active loops: {e}")
