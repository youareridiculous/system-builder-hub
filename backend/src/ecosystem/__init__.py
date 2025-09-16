"""
Ecosystem package for multi-module system orchestration

Provides system blueprints, data contracts, workflows, and orchestration
for composing multiple SBH modules into unified systems.
"""

from .blueprints import SystemBlueprint, load_system_blueprints
from .contracts import DataContract, ContractRegistry
from .orchestrator import EcosystemOrchestrator

__all__ = ['SystemBlueprint', 'load_system_blueprints', 'DataContract', 'ContractRegistry', 'EcosystemOrchestrator']
