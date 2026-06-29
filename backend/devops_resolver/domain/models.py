from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IncidentSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(StrEnum):
    created = "created"
    investigating = "investigating"
    resolved = "resolved"
    failed = "failed"


class AgentRole(StrEnum):
    planner = "planner"
    executor = "executor"
    reflector = "reflector"
    system = "system"


class ToolName(StrEnum):
    linux_command = "linux_command"
    log_reader = "log_reader"
    postgres_query = "postgres_query"
    redis_query = "redis_query"
    runbook_search = "runbook_search"
    previous_incident_search = "previous_incident_search"
    semantic_search = "semantic_search"


class ToolDecision(BaseModel):
    tool: ToolName
    purpose: str = Field(min_length=3, max_length=500)
    input: str = Field(min_length=1, max_length=4_000)
    risk: str = Field(default="read-only")


class InvestigationPlan(BaseModel):
    summary: str
    hypotheses: list[str]
    tool_decisions: list[ToolDecision]
    stop_conditions: list[str]


class ToolExecution(BaseModel):
    tool: ToolName
    input: str
    output: str
    success: bool
    duration_ms: int
    started_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReflectionResult(BaseModel):
    confidence: int = Field(ge=0, le=100)
    quality_notes: list[str]
    missing_evidence: list[str]
    should_retry: bool


class AgentTraceEvent(BaseModel):
    id: str
    incident_id: str
    role: AgentRole
    message: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentReport(BaseModel):
    incident_id: str
    root_cause: str
    suggested_fix: str
    confidence: int = Field(ge=0, le=100)
    retries: int = Field(ge=0)
    tools_executed: int = Field(ge=0)
    resolution_time_ms: int = Field(ge=0)
    evidence: list[str]
    timeline_summary: list[str]


class Incident(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    demo_key: str | None = None
    uploaded_log_path: str | None = None
    report: IncidentReport | None = None


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    category: str
    content: str
    tags: list[str]


class DemoIncident(BaseModel):
    key: str
    title: str
    description: str
    severity: IncidentSeverity
    log_lines: list[str]
    runbook_title: str
    expected_root_cause: str
    expected_fix: str
