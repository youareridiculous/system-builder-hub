"""
Agent schemas for requests and responses
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AgentRequest:
    goal: str
    project_id: Optional[str] = None
    no_llm: bool = False
    # optional: provider/model overrides

@dataclass
class AgentResult:
    project_id: str
    preview_url: Optional[str] = None
    preview_url_project: Optional[str] = None
    pages: List[Dict[str, Any]] = field(default_factory=list)
    apis: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    report: Dict[str, Any] = field(default_factory=dict)  # tester summary
    state: Dict[str, Any] = field(default_factory=dict)   # final BuilderState
