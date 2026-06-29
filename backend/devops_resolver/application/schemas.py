from datetime import datetime

from pydantic import BaseModel, Field

from devops_resolver.domain.models import (
    AgentTraceEvent,
    DemoIncident,
    Incident,
    IncidentReport,
    IncidentSeverity,
)


class CreateIncidentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=4_000)
    severity: IncidentSeverity = IncidentSeverity.high
    demo_key: str | None = None


class CreateIncidentResponse(BaseModel):
    incident: Incident


class IncidentHistoryResponse(BaseModel):
    incidents: list[Incident]


class InvestigationResponse(BaseModel):
    incident: Incident
    report: IncidentReport | None


class DemoIncidentResponse(BaseModel):
    demos: list[DemoIncident]


class RunbookResponse(BaseModel):
    id: str
    title: str
    category: str
    tags: list[str]
    content: str


class StreamEvent(BaseModel):
    type: str
    incident_id: str
    created_at: datetime
    trace: AgentTraceEvent | None = None
    incident: Incident | None = None
    report: IncidentReport | None = None
