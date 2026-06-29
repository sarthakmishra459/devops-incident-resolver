import asyncio
from collections import defaultdict

from devops_resolver.application.schemas import StreamEvent


class InMemoryEventBus:
    """Small async pub/sub bus used for local streaming and tests."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[StreamEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, event: StreamEvent) -> None:
        async with self._lock:
            subscribers = list(self._subscribers[event.incident_id])

        for queue in subscribers:
            await queue.put(event)

    async def subscribe(self, incident_id: str) -> asyncio.Queue[StreamEvent]:
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[incident_id].add(queue)
        return queue

    async def unsubscribe(self, incident_id: str, queue: asyncio.Queue[StreamEvent]) -> None:
        async with self._lock:
            self._subscribers[incident_id].discard(queue)
            if not self._subscribers[incident_id]:
                del self._subscribers[incident_id]
