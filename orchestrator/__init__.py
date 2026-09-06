"""
Orchestrator package integrating CrewAI agents with the FastAPI validation pipeline.
"""

import sys
from pathlib import Path

# Ensure workspace paths are available
_workspace_root = Path(__file__).resolve().parent.parent
_agents_src = _workspace_root / "agents" / "src"
_validator_root = _workspace_root / "validator"

for _p in [str(_workspace_root), str(_agents_src), str(_validator_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from orchestrator.adapters.spec_adapter import (
    adapt_specification,
    build_safety_policy,
    parse_duration_seconds,
    resolve_payload_body,
    normalize_threshold_rule,
    AgentEvent,
    AdaptationResult,
)

__all__ = [
    "adapt_specification",
    "build_safety_policy",
    "parse_duration_seconds",
    "resolve_payload_body",
    "normalize_threshold_rule",
    "AgentEvent",
    "AdaptationResult",
]
