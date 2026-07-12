import asyncio
import logging
from collections import defaultdict

from app.models.schemas import PipelineEvent

log = logging.getLogger(__name__)


class EventBus:
    """Per-run pub/sub used to stream pipeline progress to WebSocket clients."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[PipelineEvent]]] = defaultdict(set)
        self._history: dict[str, list[PipelineEvent]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, event: PipelineEvent) -> None:
        async with self._lock:
            self._history[event.run_id].append(event)
            queues = list(self._subscribers[event.run_id])
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                log.warning("Dropping event for slow subscriber on run %s", event.run_id)

    async def subscribe(self, run_id: str) -> tuple[asyncio.Queue[PipelineEvent], list[PipelineEvent]]:
        q: asyncio.Queue[PipelineEvent] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers[run_id].add(q)
            replay = list(self._history[run_id])
        return q, replay

    async def unsubscribe(self, run_id: str, q: asyncio.Queue[PipelineEvent]) -> None:
        async with self._lock:
            self._subscribers[run_id].discard(q)


bus = EventBus()
