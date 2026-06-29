from abc import ABC, abstractmethod

from devops_resolver.domain.models import AgentTraceEvent, Incident, KnowledgeDocument


class IncidentRepository(ABC):
    @abstractmethod
    async def create(self, incident: Incident) -> Incident:
        raise NotImplementedError

    @abstractmethod
    async def get(self, incident_id: str) -> Incident | None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[Incident]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, incident: Incident) -> Incident:
        raise NotImplementedError


class TraceRepository(ABC):
    @abstractmethod
    async def append(self, event: AgentTraceEvent) -> AgentTraceEvent:
        raise NotImplementedError

    @abstractmethod
    async def list_for_incident(self, incident_id: str) -> list[AgentTraceEvent]:
        raise NotImplementedError


class KnowledgeRepository(ABC):
    @abstractmethod
    async def all_documents(self) -> list[KnowledgeDocument]:
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[KnowledgeDocument]:
        raise NotImplementedError
