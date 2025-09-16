"""
SBH Meta-Builder v2
Multi-agent, iterative scaffold generation with approval gates.
"""

from .models import *
from .orchestrator import MetaBuilderOrchestrator
# from .agents import *
from .api import meta_builder_v2
from .ui_routes import meta_builder_v2_ui

__version__ = "2.0.0"
__all__ = [
    "MetaBuilderOrchestrator",
    "meta_builder_v2",
    "meta_builder_v2_ui"
]
