"""
Domain models and schema definitions for the Orchestrator service.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RunState(str, Enum):
    CREATED = "CREATED"
    ANALYSING = "ANALYSING"
    PLANNING = "PLANNING"
    CRITIC_REVIEW = "CRITIC_REVIEW"
    VALIDATING = "VALIDATING"
    BUILDING = "BUILDING"
    EXECUTING = "EXECUTING"
    ANALYSING_RESULTS = "ANALYSING_RESULTS"
    DECIDING_NEXT_TEST = "DECIDING_NEXT_TEST"
    SUMMARIZING = "SUMMARIZING"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"

    # Terminal failure and stop states
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class AgentEvent(BaseModel):
    """
    Structured event emitted during state transitions and agent actions.
    Streamed to the frontend via SSE / WebSocket.
    """
    event_id: Optional[str] = None
    run_id: str = Field(..., description="ID of the associated run")
    state: RunState = Field(..., description="State when event was emitted")
    event_type: str = Field(..., description="Category: state_change, agent_output, validation_result, etc.")
    source: str = Field(default="orchestrator", description="Component or agent that emitted the event")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
    message: str = Field(..., description="Human-readable event message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured payload or artifact references")


class CreateRunRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language performance testing requirement")
    mock_mode: bool = Field(default=True, description="Whether to execute pipeline in mock mode or live LLM mode")
    target_base_url: Optional[str] = Field(default=None, description="Optional target base URL override")


class RunSummary(BaseModel):
    run_id: str
    prompt: str
    state: RunState
    mock_mode: bool
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class RunDetail(RunSummary):
    requirement_spec: Optional[Dict[str, Any]] = None
    performance_plan: Optional[Dict[str, Any]] = None
    test_data_plan: Optional[Dict[str, Any]] = None
    test_specification: Optional[Dict[str, Any]] = None
    adapted_test_spec: Optional[Dict[str, Any]] = None
    critic_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    compiled_k6_script: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    decision_result: Optional[Dict[str, Any]] = None
    events: List[AgentEvent] = Field(default_factory=list)

