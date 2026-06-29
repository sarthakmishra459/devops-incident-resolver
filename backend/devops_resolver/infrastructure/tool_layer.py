import asyncio
import re
import time
from pathlib import Path

import aiofiles
import aiofiles.os

from devops_resolver.domain.models import DemoIncident, ToolExecution, ToolName
from devops_resolver.domain.repositories import KnowledgeRepository
from devops_resolver.infrastructure.demo_data import demo_incidents
from devops_resolver.infrastructure.vector_store import FaissKnowledgeIndex
from devops_resolver.shared.config import Settings
from devops_resolver.shared.time import utc_now

_SAFE_COMMANDS = {
    "cat",
    "df",
    "du",
    "free",
    "grep",
    "head",
    "iostat",
    "journalctl",
    "kubectl",
    "netstat",
    "ps",
    "redis-cli",
    "ss",
    "systemctl",
    "tail",
    "top",
    "uptime",
    "vmstat",
}

_DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(rm|mkfs|shutdown|reboot|halt|poweroff|kill|pkill|drop|delete|truncate|update|insert)\b",
    re.IGNORECASE,
)


class ToolLayer:
    def __init__(
        self,
        settings: Settings,
        knowledge_repository: KnowledgeRepository,
        vector_index: FaissKnowledgeIndex,
    ) -> None:
        self._settings = settings
        self._knowledge_repository = knowledge_repository
        self._vector_index = vector_index

    async def execute(
        self,
        tool: ToolName,
        tool_input: str,
        *,
        incident_log_path: str | None = None,
        demo_key: str | None = None,
    ) -> ToolExecution:
        started = utc_now()
        start = time.perf_counter()
        try:
            output = await self._dispatch(tool, tool_input, incident_log_path, demo_key)
            success = True
        except Exception as exc:
            output = f"{type(exc).__name__}: {exc}"
            success = False
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ToolExecution(
            tool=tool,
            input=tool_input,
            output=output[: self._settings.max_command_output_chars],
            success=success,
            duration_ms=duration_ms,
            started_at=started,
        )

    async def _dispatch(
        self,
        tool: ToolName,
        tool_input: str,
        incident_log_path: str | None,
        demo_key: str | None,
    ) -> str:
        if tool == ToolName.linux_command:
            return await self._run_linux_command(tool_input, demo_key)
        if tool == ToolName.log_reader:
            return await self._read_logs(tool_input, incident_log_path, demo_key)
        if tool == ToolName.postgres_query:
            return await self._query_postgres(tool_input, demo_key)
        if tool == ToolName.redis_query:
            return await self._query_redis(tool_input, demo_key)
        if tool == ToolName.runbook_search:
            return await self._search_documents(tool_input, "runbook")
        if tool == ToolName.previous_incident_search:
            return await self._search_documents(tool_input, "previous_incident")
        if tool == ToolName.semantic_search:
            return await self._semantic_search(tool_input)
        raise ValueError(f"Unsupported tool: {tool}")

    async def _run_linux_command(self, command: str, demo_key: str | None) -> str:
        command = command.strip()
        executable = command.split(maxsplit=1)[0] if command else ""
        if _DESTRUCTIVE_PATTERNS.search(command):
            raise ValueError("Refusing destructive command in autonomous investigation")
        if executable not in _SAFE_COMMANDS:
            raise ValueError(f"Command '{executable}' is not in the read-only allowlist")

        demo = _demo_by_key(demo_key)
        if demo is not None:
            return _simulate_command(command, demo.key)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=self._settings.command_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise TimeoutError(
                f"Command timed out after {self._settings.command_timeout_seconds}s"
            ) from exc
        return stdout.decode("utf-8", errors="replace")

    async def _read_logs(
        self,
        query: str,
        incident_log_path: str | None,
        demo_key: str | None,
    ) -> str:
        demo = _demo_by_key(demo_key)
        if demo is not None:
            return "\n".join(demo.log_lines)

        if not incident_log_path:
            return "No uploaded log file was provided for this incident."
        path = Path(incident_log_path)
        if not await aiofiles.os.path.exists(path) or not await aiofiles.os.path.isfile(path):
            return f"Log file is not available: {path}"
        async with aiofiles.open(path, encoding="utf-8", errors="replace") as handle:
            content = await handle.read()
        terms = [term.lower() for term in query.split() if len(term) > 2]
        matching = [
            line
            for line in content.splitlines()
            if not terms or any(term in line.lower() for term in terms)
        ]
        return "\n".join(matching[-200:]) or content[-20_000:]

    async def _query_postgres(self, query: str, demo_key: str | None) -> str:
        demo = _demo_by_key(demo_key)
        if demo is not None or not self._settings.database_enabled:
            key = demo.key if demo else "local"
            return _simulate_postgres(query, key)
        return (
            "External PostgreSQL execution is disabled for autonomous read safety in this build. "
            "Configure a read-only query adapter before enabling live database access."
        )

    async def _query_redis(self, query: str, demo_key: str | None) -> str:
        demo = _demo_by_key(demo_key)
        if demo is not None or not self._settings.redis_enabled:
            key = demo.key if demo else "local"
            return _simulate_redis(query, key)
        return (
            "External Redis execution is disabled for autonomous read safety in this build. "
            "Configure a read-only query adapter before enabling live Redis access."
        )

    async def _search_documents(self, query: str, category: str) -> str:
        documents = await self._knowledge_repository.search(query, limit=8)
        filtered = [doc for doc in documents if doc.category == category] or documents
        return "\n\n".join(
            f"# {doc.title}\ncategory={doc.category} tags={','.join(doc.tags)}\n{doc.content}"
            for doc in filtered[:5]
        )

    async def _semantic_search(self, query: str) -> str:
        results = await self._vector_index.search(query, limit=5)
        return "\n\n".join(
            f"# {result.document.title} score={result.score:.3f}\n{result.document.content}"
            for result in results
        )


def _demo_by_key(demo_key: str | None) -> DemoIncident | None:
    if demo_key is None:
        return None
    return next((demo for demo in demo_incidents() if demo.key == demo_key), None)


def _simulate_command(command: str, demo_key: str) -> str:
    if "df" in command:
        used = "97%" if demo_key in {"disk-full", "postgresql-down"} else "62%"
        return f"Filesystem      Size  Used Avail Use% Mounted on\n/dev/nvme0n1p1  200G  194G  6G {used} /var/lib/postgresql"
    if "free" in command:
        if demo_key in {"out-of-memory", "memory-leak", "redis-memory-full"}:
            return "Mem: 15872 15190 212 120 470 320\nSwap: 2048 2048 0"
        return "Mem: 15872 9231 4012 200 2629 5200\nSwap: 2048 128 1920"
    if "uptime" in command or "top" in command:
        load = "18.92, 17.44, 12.01" if demo_key == "high-cpu" else "2.11, 1.90, 1.73"
        return f"07:14:26 up 19 days,  load average: {load}"
    if "iostat" in command or "vmstat" in command:
        wait = "47.9" if demo_key == "high-disk-io" else "4.1"
        return f"avg-cpu: %user %system %iowait\n          18.1   9.2     {wait}"
    if "kubectl" in command:
        if demo_key == "service-crash":
            return "billing-7dd8c9b89b-zvk9s 0/1 CrashLoopBackOff 12 18m"
        return "api-prod-03 1/1 Running 0 4d"
    if "systemctl" in command:
        return (
            "postgresql.service loaded failed failed PostgreSQL database server"
            if demo_key == "postgresql-down"
            else "service active"
        )
    return f"Simulated read-only command output for demo '{demo_key}': {command}"


def _simulate_postgres(query: str, demo_key: str) -> str:
    if demo_key in {"postgresql-down", "disk-full", "nginx-502"}:
        return (
            "connections=100 max_connections=100; longest_transaction=00:24:18; "
            "wait_event=ClientRead; recent_error='No space left on device'"
        )
    return f"Read-only PostgreSQL demo result for query: {query}"


def _simulate_redis(query: str, demo_key: str) -> str:
    if demo_key == "redis-memory-full":
        return "used_memory=15887024128 maxmemory=16106127360 evicted_keys=0 ttl_missing_session_keys=1382042"
    return f"Read-only Redis demo result for query: {query}"
