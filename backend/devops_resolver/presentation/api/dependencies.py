from functools import lru_cache

from devops_resolver.application.agents import PlannerAgent, ReflectorAgent, ReporterAgent
from devops_resolver.application.event_bus import InMemoryEventBus
from devops_resolver.application.use_cases import IncidentService
from devops_resolver.infrastructure.repositories import (
    InMemoryIncidentRepository,
    InMemoryTraceRepository,
    StaticKnowledgeRepository,
)
from devops_resolver.infrastructure.tool_layer import ToolLayer
from devops_resolver.infrastructure.vector_store import FaissKnowledgeIndex
from devops_resolver.shared.config import Settings, get_settings


class ApplicationContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.incidents = InMemoryIncidentRepository()
        self.traces = InMemoryTraceRepository()
        self.knowledge = StaticKnowledgeRepository()
        self.event_bus = InMemoryEventBus()
        self.vector_index = FaissKnowledgeIndex(self.knowledge)
        self.tool_layer = ToolLayer(settings, self.knowledge, self.vector_index)
        self.incident_service = IncidentService(
            incident_repository=self.incidents,
            trace_repository=self.traces,
            knowledge_repository=self.knowledge,
            event_bus=self.event_bus,
            tool_layer=self.tool_layer,
            planner=PlannerAgent(settings),
            reflector=ReflectorAgent(settings),
            reporter=ReporterAgent(),
        )

    async def startup(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings.vector_index_dir.mkdir(parents=True, exist_ok=True)
        await self.vector_index.hydrate()


@lru_cache
def get_container() -> ApplicationContainer:
    return ApplicationContainer(get_settings())


def get_incident_service() -> IncidentService:
    return get_container().incident_service
