"""
Agent planner - converts natural language goals to BuilderState
"""
import logging
from typing import Dict, Any
from ..builder_schema import VALID_NODE_TYPES, slugify
from .heuristics import detect_pattern, get_pattern_nodes

logger = logging.getLogger(__name__)

def plan_no_llm(goal: str) -> Dict[str, Any]:
    """Very simple heuristics → MVP BuilderState"""
    # Detect pattern based on goal keywords
    pattern = detect_pattern(goal)
    nodes = get_pattern_nodes(pattern)
    edges = []

    logger.info(f"Generated plan for goal '{goal}': pattern={pattern}, {len(nodes)} nodes")
    return {
        "version": "v1",
        "nodes": nodes,
        "edges": edges,
        "metadata": {"goal": goal, "pattern": pattern}
    }

def plan_with_llm(goal: str) -> Dict[str, Any]:
    """LLM-based planning (stub for v0)"""
    # TODO: Implement LLM planning in v0.5
    logger.info("LLM planning not implemented yet, falling back to heuristic planning")
    return plan_no_llm(goal)
