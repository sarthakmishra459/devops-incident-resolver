import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from devops_resolver.application.agents import PlannerAgent, ReflectorAgent, ReporterAgent
from devops_resolver.application.event_bus import InMemoryEventBus
from devops_resolver.application.schemas import CreateIncidentRequest, StreamEvent
from devops_resolver.domain.models import (
    AgentRole,
    AgentTraceEvent,
    DemoIncident,
    Incident,
    IncidentStatus,
    KnowledgeDocument,
    ToolExecution,
)
from devops_resolver.domain.repositories import (
    IncidentRepository,
    KnowledgeRepository,
    TraceRepository,
)
from devops_resolver.infrastructure.demo_data import demo_incidents
from devops_resolver.infrastructure.tool_layer import ToolLayer
from devops_resolver.shared.ids import new_id
from devops_resolver.shared.time import utc_now


class IncidentService:
    def __init__(
        self,
        incident_repository: IncidentRepository,
        trace_repository: TraceRepository,
        knowledge_repository: KnowledgeRepository,
        event_bus: InMemoryEventBus,
        tool_layer: ToolLayer,
        planner: PlannerAgent,
        reflector: ReflectorAgent,
        reporter: ReporterAgent,
    ) -> None:
        self._incidents = incident_repository
        self._traces = trace_repository
        self._knowledge = knowledge_repository
        self._events = event_bus
        self._tools = tool_layer
        self._planner = planner
        self._reflector = reflector
        self._reporter = reporter

    async def create_incident(
        self, request: CreateIncidentRequest, uploaded_log_path: str | None = None
    ) -> Incident:
        now = utc_now()
        incident = Incident(
            id=new_id("inc"),
            title=request.title,
            description=request.description,
            severity=request.severity,
            status=IncidentStatus.created,
            created_at=now,
            updated_at=now,
            demo_key=request.demo_key,
            uploaded_log_path=uploaded_log_path,
        )
        await self._incidents.create(incident)
        await self._append_trace(
            incident.id,
            AgentRole.system,
            "Incident created and queued for investigation.",
            {"severity": incident.severity.value, "demo_key": incident.demo_key},
        )
        return incident

    async def investigate(self, incident_id: str) -> Incident:
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise KeyError(f"Incident not found: {incident_id}")

        started = time.perf_counter()
        incident = incident.model_copy(
            update={"status": IncidentStatus.investigating, "updated_at": utc_now()}
        )
        await self._incidents.update(incident)
        await self._publish(
            StreamEvent(
                type="incident.updated",
                incident_id=incident.id,
                created_at=utc_now(),
                incident=incident,
            )
        )

        executions: list[ToolExecution] = []
        retries = 0
        reflection = None
        while True:
            plan = await self._planner.plan(incident, executions)
            await self._append_trace(
                incident.id,
                AgentRole.planner,
                plan.summary,
                {
                    "hypotheses": plan.hypotheses,
                    "tool_decisions": [
                        decision.model_dump(mode="json") for decision in plan.tool_decisions
                    ],
                },
            )

            for decision in plan.tool_decisions:
                await self._append_trace(
                    incident.id,
                    AgentRole.executor,
                    f"Executing {decision.tool.value}: {decision.purpose}",
                    {"tool_input": decision.input, "risk": decision.risk},
                )
                execution = await self._tools.execute(
                    decision.tool,
                    decision.input,
                    incident_log_path=incident.uploaded_log_path,
                    demo_key=incident.demo_key,
                )
                executions.append(execution)
                await self._append_trace(
                    incident.id,
                    AgentRole.executor,
                    execution.output,
                    {
                        "tool": execution.tool.value,
                        "success": execution.success,
                        "duration_ms": execution.duration_ms,
                    },
                )

            reflection = await self._reflector.reflect(incident, plan, executions, retries)
            await self._append_trace(
                incident.id,
                AgentRole.reflector,
                f"Confidence {reflection.confidence}%. Retry required: {reflection.should_retry}.",
                reflection.model_dump(mode="json"),
            )
            if not reflection.should_retry:
                break
            retries += 1

        assert reflection is not None
        report = await self._reporter.report(
            incident,
            executions,
            reflection,
            retries,
            int((time.perf_counter() - started) * 1000),
        )
        incident = incident.model_copy(
            update={"status": IncidentStatus.resolved, "updated_at": utc_now(), "report": report}
        )
        await self._incidents.update(incident)
        await self._append_trace(
            incident.id,
            AgentRole.system,
            f"Final report created with confidence {report.confidence}%.",
            report.model_dump(mode="json"),
        )
        await self._publish(
            StreamEvent(
                type="incident.resolved",
                incident_id=incident.id,
                created_at=utc_now(),
                incident=incident,
                report=report,
            )
        )
        return incident

    async def stream(self, incident_id: str) -> AsyncIterator[StreamEvent]:
        queue = await self._events.subscribe(incident_id)
        try:
            for trace in await self._traces.list_for_incident(incident_id):
                yield StreamEvent(
                    type="trace.replay",
                    incident_id=incident_id,
                    created_at=trace.created_at,
                    trace=trace,
                )
            while True:
                yield await queue.get()
        finally:
            await self._events.unsubscribe(incident_id, queue)

    async def list_incidents(self) -> list[Incident]:
        return await self._incidents.list_recent()

    async def get_incident(self, incident_id: str) -> Incident | None:
        return await self._incidents.get(incident_id)

    async def list_traces(self, incident_id: str) -> list[AgentTraceEvent]:
        return await self._traces.list_for_incident(incident_id)

    async def list_runbooks(self) -> list[KnowledgeDocument]:
        documents = await self._knowledge.all_documents()
        return [document for document in documents if document.category == "runbook"]

    async def list_demo_incidents(self) -> list[DemoIncident]:
        return demo_incidents()

    async def investigate_background(self, incident_id: str) -> None:
        try:
            await self.investigate(incident_id)
        except Exception as exc:
            incident = await self._incidents.get(incident_id)
            if incident is not None:
                failed = incident.model_copy(
                    update={"status": IncidentStatus.failed, "updated_at": utc_now()}
                )
                await self._incidents.update(failed)
            await self._append_trace(
                incident_id,
                AgentRole.system,
                f"Investigation failed: {type(exc).__name__}: {exc}",
                {"error": type(exc).__name__},
            )

    def schedule_investigation(self, incident_id: str) -> None:
        task = asyncio.create_task(self.investigate_background(incident_id))
        task.add_done_callback(_observe_task_failure)

    async def _append_trace(
        self,
        incident_id: str,
        role: AgentRole,
        message: str,
        metadata: dict[str, Any],
    ) -> AgentTraceEvent:
        trace = AgentTraceEvent(
            id=new_id("trace"),
            incident_id=incident_id,
            role=role,
            message=message,
            created_at=utc_now(),
            metadata=metadata,
        )
        await self._traces.append(trace)
        await self._publish(
            StreamEvent(
                type="trace", incident_id=incident_id, created_at=trace.created_at, trace=trace
            )
        )
        return trace

    async def _publish(self, event: StreamEvent) -> None:
        await self._events.publish(event)


def _observe_task_failure(completed: asyncio.Task[None]) -> None:
    completed.exception()
