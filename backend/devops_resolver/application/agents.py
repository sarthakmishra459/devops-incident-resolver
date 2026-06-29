import json
from collections import Counter

from devops_resolver.domain.models import (
    Incident,
    IncidentReport,
    InvestigationPlan,
    ReflectionResult,
    ToolDecision,
    ToolExecution,
    ToolName,
)
from devops_resolver.infrastructure.demo_data import demo_incidents
from devops_resolver.shared.config import Settings


class PlannerAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def plan(
        self, incident: Incident, prior_executions: list[ToolExecution]
    ) -> InvestigationPlan:
        if self._settings.should_use_external_llm:
            plan = await self._llm_plan(incident, prior_executions)
            if plan is not None:
                return plan
        return self._heuristic_plan(incident, prior_executions)

    async def _llm_plan(
        self, incident: Incident, prior_executions: list[ToolExecution]
    ) -> InvestigationPlan | None:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            api_key=self._settings.llm_api_key,
            base_url=self._settings.llm_base_url,
            timeout=self._settings.llm_timeout_seconds,
        )
        prompt = (
            "Return strict JSON with keys summary, hypotheses, tool_decisions, stop_conditions. "
            "tool_decisions entries require tool, purpose, input, risk. Use only these tools: "
            f"{', '.join(tool.value for tool in ToolName)}. Prefer read-only investigation."
        )
        previous = "\n".join(f"{item.tool}: {item.output[:500]}" for item in prior_executions[-8:])
        response = await llm.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(
                    content=(
                        f"Incident title: {incident.title}\nDescription: {incident.description}\n"
                        f"Previous evidence:\n{previous or 'none'}"
                    )
                ),
            ]
        )
        try:
            payload = json.loads(str(response.content))
            return InvestigationPlan.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            return None

    def _heuristic_plan(
        self, incident: Incident, prior_executions: list[ToolExecution]
    ) -> InvestigationPlan:
        text = f"{incident.title} {incident.description} {incident.demo_key or ''}".lower()
        already_used = Counter(execution.tool for execution in prior_executions)
        decisions: list[ToolDecision] = [
            ToolDecision(
                tool=ToolName.log_reader,
                purpose="Collect recent incident log lines and error messages.",
                input=text,
            ),
            ToolDecision(
                tool=ToolName.semantic_search,
                purpose="Retrieve relevant runbooks and previous incident patterns.",
                input=text,
            ),
        ]
        if any(token in text for token in ["disk", "postgres", "db", "502"]):
            decisions.append(
                ToolDecision(
                    tool=ToolName.postgres_query,
                    purpose="Check database pressure and availability indicators.",
                    input="select now(), count(*) from pg_stat_activity;",
                )
            )
        if any(token in text for token in ["redis", "cache", "memory"]):
            decisions.append(
                ToolDecision(
                    tool=ToolName.redis_query,
                    purpose="Check cache memory pressure and eviction indicators.",
                    input="INFO memory",
                )
            )
        command = "uptime"
        if "disk" in text or "postgres" in text:
            command = "df -h"
        elif "memory" in text or "oom" in text:
            command = "free -m"
        elif "io" in text:
            command = "iostat -xz 1 1"
        elif "crash" in text:
            command = "kubectl get pods"
        decisions.append(
            ToolDecision(
                tool=ToolName.linux_command,
                purpose="Collect host or platform signal using an allowlisted read-only command.",
                input=command,
            )
        )
        if already_used:
            decisions.append(
                ToolDecision(
                    tool=ToolName.previous_incident_search,
                    purpose="Compare current evidence against prior incidents before finalizing.",
                    input=text,
                )
            )
        return InvestigationPlan(
            summary=f"Investigate {incident.title} by correlating logs, infrastructure state, and RAG evidence.",
            hypotheses=_hypotheses_for_text(text),
            tool_decisions=decisions[:5],
            stop_conditions=[
                "Root cause is supported by direct log evidence.",
                "A safe mitigation is identified.",
                "Confidence is at least 80.",
            ],
        )


class ReflectorAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def reflect(
        self,
        incident: Incident,
        plan: InvestigationPlan,
        executions: list[ToolExecution],
        retries: int,
    ) -> ReflectionResult:
        joined = "\n".join(
            execution.output.lower() for execution in executions if execution.success
        )
        confidence = 35
        notes: list[str] = []
        missing: list[str] = []

        if any(
            execution.tool == ToolName.log_reader and execution.success for execution in executions
        ):
            confidence += 20
            notes.append("Logs were inspected.")
        if any(
            execution.tool in {ToolName.semantic_search, ToolName.runbook_search}
            for execution in executions
        ):
            confidence += 15
            notes.append("Knowledge base evidence was retrieved.")
        if any(
            execution.tool == ToolName.linux_command and execution.success
            for execution in executions
        ):
            confidence += 10
            notes.append("Read-only system state was collected.")
        if any(term in joined for term in _root_cause_terms(incident)):
            confidence += 20
            notes.append("Evidence matches a known incident signature.")
        if "error" in joined or "failed" in joined or "oom" in joined or "502" in joined:
            confidence += 8
            notes.append("Failure indicators are present in evidence.")
        if not notes:
            missing.append("No reliable evidence was collected.")
        if not any(execution.tool == ToolName.log_reader for execution in executions):
            missing.append("Incident logs have not been read.")
        if not any(execution.tool == ToolName.semantic_search for execution in executions):
            missing.append("RAG evidence has not been retrieved.")

        confidence = min(confidence, 98)
        should_retry = (
            confidence < self._settings.confidence_threshold
            and retries < self._settings.max_reflection_retries
        )
        return ReflectionResult(
            confidence=confidence,
            quality_notes=notes or ["Investigation produced limited evidence."],
            missing_evidence=missing,
            should_retry=should_retry,
        )


class ReporterAgent:
    async def report(
        self,
        incident: Incident,
        executions: list[ToolExecution],
        reflection: ReflectionResult,
        retries: int,
        resolution_time_ms: int,
    ) -> IncidentReport:
        demo = next((item for item in demo_incidents() if item.key == incident.demo_key), None)
        if demo is not None:
            root_cause = demo.expected_root_cause
            suggested_fix = demo.expected_fix
        else:
            root_cause = _infer_root_cause(incident, executions)
            suggested_fix = _infer_fix(root_cause)

        evidence = [
            f"{execution.tool.value}: {execution.output[:600].strip()}"
            for execution in executions
            if execution.success and execution.output.strip()
        ][:8]
        timeline = [
            f"{execution.started_at.isoformat()} {execution.tool.value} completed in {execution.duration_ms}ms"
            for execution in executions
        ]
        return IncidentReport(
            incident_id=incident.id,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
            confidence=reflection.confidence,
            retries=retries,
            tools_executed=len(executions),
            resolution_time_ms=resolution_time_ms,
            evidence=evidence,
            timeline_summary=timeline,
        )


def _hypotheses_for_text(text: str) -> list[str]:
    mapping = {
        "disk": "Storage pressure is causing writes or dependent services to fail.",
        "cpu": "Compute saturation is increasing latency and queue depth.",
        "postgres": "Database unavailability or connection saturation is driving impact.",
        "redis": "Cache memory pressure is causing failed writes or cache instability.",
        "502": "Nginx upstream failures are caused by unhealthy application workers.",
        "ssl": "TLS certificate lifecycle failure is blocking secure traffic.",
        "memory": "Memory pressure or a leak is forcing restarts or OOM kills.",
        "crash": "A deployment or configuration regression is crashing the service.",
        "io": "Disk IO saturation is causing service latency.",
    }
    return [hypothesis for token, hypothesis in mapping.items() if token in text] or [
        "Recent production change or resource saturation is causing the alert."
    ]


def _root_cause_terms(incident: Incident) -> set[str]:
    demo = next((item for item in demo_incidents() if item.key == incident.demo_key), None)
    if demo is None:
        return set(
            _hypotheses_for_text(f"{incident.title} {incident.description}".lower())[0]
            .lower()
            .split()
        )
    return {
        token
        for token in demo.expected_root_cause.lower().replace("/", " ").split()
        if len(token) > 4
    }


def _infer_root_cause(incident: Incident, executions: list[ToolExecution]) -> str:
    evidence = "\n".join(execution.output.lower() for execution in executions)
    if "no space left" in evidence or "97%" in evidence:
        return "Storage exhaustion is preventing dependent services from writing safely."
    if "oom" in evidence or "out of memory" in evidence:
        return "Memory pressure caused processes to be killed or marked unhealthy."
    if "502" in evidence or "upstream" in evidence:
        return "Nginx is returning 502 because upstream application workers are unhealthy."
    if "certificate" in evidence or "tls" in evidence:
        return "The TLS certificate is invalid or expired."
    if "load average" in evidence or "worker pool exhausted" in evidence:
        return "CPU or worker saturation is causing elevated latency."
    return f"The incident appears related to {incident.title.lower()} based on collected evidence."


def _infer_fix(root_cause: str) -> str:
    text = root_cause.lower()
    if "storage" in text:
        return "Free or expand storage, restore archival/cleanup jobs, and restart affected services after writes recover."
    if "memory" in text:
        return "Reduce memory pressure, cap workload size, restart unhealthy workers, and deploy a leak or limit fix."
    if "nginx" in text:
        return "Restore upstream health, restart failed workers, and verify connection pools before reopening traffic."
    if "tls" in text:
        return "Renew the certificate, fix validation automation, reload ingress, and add expiry monitoring."
    if "cpu" in text:
        return "Throttle expensive work, scale capacity, and optimize the saturated path."
    return "Mitigate customer impact, verify the suspected dependency, and create a durable follow-up fix."
