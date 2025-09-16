"""
Evaluation Lab v1

A comprehensive benchmarking system for System Builder Hub that runs benchmarks
on a schedule and on PRs, computes quality/latency/cost KPIs, enforces regression
gates in CI, respects Privacy Modes, and provides dashboards/reports.
"""

__version__ = "1.0.0"

from .specs import GoldenCase, ScenarioBundle, KPIGuard
from .runner import EvaluationRunner
from .assertions import AssertionEngine
from .storage import EvaluationStorage
from .compare import ComparisonEngine
from .costs import CostCalculator

__all__ = [
    "GoldenCase",
    "ScenarioBundle", 
    "KPIGuard",
    "EvaluationRunner",
    "AssertionEngine",
    "EvaluationStorage",
    "ComparisonEngine",
    "CostCalculator",
]
