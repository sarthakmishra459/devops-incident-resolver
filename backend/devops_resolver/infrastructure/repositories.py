from asyncio import Lock

from devops_resolver.domain.models import AgentTraceEvent, Incident, KnowledgeDocument
from devops_resolver.domain.repositories import (
    IncidentRepository,
    KnowledgeRepository,
    TraceRepository,
)
from devops_resolver.infrastructure.demo_data import knowledge_documents


class InMemoryIncidentRepository(IncidentRepository):
    def __init__(self) -> None:
        self._items: dict[str, Incident] = {}
        self._lock = Lock()

    async def create(self, incident: Incident) -> Incident:
        async with self._lock:
            self._items[incident.id] = incident
        return incident

    async def get(self, incident_id: str) -> Incident | None:
        async with self._lock:
            return self._items.get(incident_id)

    async def list_recent(self, limit: int = 50) -> list[Incident]:
        async with self._lock:
            incidents = sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)
        return incidents[:limit]

    async def update(self, incident: Incident) -> Incident:
        async with self._lock:
            self._items[incident.id] = incident
        return incident


class InMemoryTraceRepository(TraceRepository):
    def __init__(self) -> None:
        self._items: dict[str, list[AgentTraceEvent]] = {}
        self._lock = Lock()

    async def append(self, event: AgentTraceEvent) -> AgentTraceEvent:
        async with self._lock:
            self._items.setdefault(event.incident_id, []).append(event)
        return event

    async def list_for_incident(self, incident_id: str) -> list[AgentTraceEvent]:
        async with self._lock:
            return list(self._items.get(incident_id, []))


class StaticKnowledgeRepository(KnowledgeRepository):
    def __init__(self, documents: list[KnowledgeDocument] | None = None) -> None:
        self._documents = documents or knowledge_documents()

    async def all_documents(self) -> list[KnowledgeDocument]:
        return list(self._documents)

    async def search(self, query: str, limit: int = 5) -> list[KnowledgeDocument]:
        terms = {term.lower() for term in query.replace("-", " ").split() if len(term) > 2}

        def score(document: KnowledgeDocument) -> int:
            haystack = f"{document.title} {document.content} {' '.join(document.tags)}".lower()
            return sum(1 for term in terms if term in haystack)

        ranked = sorted(self._documents, key=score, reverse=True)
        return [document for document in ranked if score(document) > 0][:limit] or ranked[:limit]
