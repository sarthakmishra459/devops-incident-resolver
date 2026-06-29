import asyncio

import pytest

from devops_resolver.application.schemas import CreateIncidentRequest
from devops_resolver.domain.models import IncidentSeverity, IncidentStatus
from devops_resolver.presentation.api.dependencies import get_container


@pytest.mark.agent
def test_demo_incident_runs_full_agent_loop() -> None:
    asyncio.run(_assert_demo_incident_runs_full_agent_loop())


async def _assert_demo_incident_runs_full_agent_loop() -> None:
    container = get_container()
    await container.startup()
    service = container.incident_service

    incident = await service.create_incident(
        CreateIncidentRequest(
            title="Disk Full",
            description="Disk usage exceeded 95% on payments-db-01",
            severity=IncidentSeverity.critical,
            demo_key="disk-full",
        )
    )

    resolved = await service.investigate(incident.id)
    traces = await service.list_traces(incident.id)

    assert resolved.status == IncidentStatus.resolved
    assert resolved.report is not None
    assert resolved.report.confidence >= 80
    assert "WAL" in resolved.report.root_cause
    assert resolved.report.tools_executed >= 3
    assert {trace.role.value for trace in traces} >= {"planner", "executor", "reflector", "system"}
