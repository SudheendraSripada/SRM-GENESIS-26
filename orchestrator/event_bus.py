"""
Async pub/sub event bus for streaming AgentEvents over SSE and WebSockets.
"""

import asyncio
from typing import Dict, List, Set
from orchestrator.models import AgentEvent


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribes an async listener queue to events for a specific run_id."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = set()
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        """Removes a subscriber queue."""
        async with self._lock:
            if run_id in self._subscribers:
                self._subscribers[run_id].discard(queue)
                if not self._subscribers[run_id]:
                    del self._subscribers[run_id]

    async def publish(self, event: AgentEvent):
        """Dispatches an event to all active subscriber queues for event.run_id."""
        run_id = event.run_id
        async with self._lock:
            queues = list(self._subscribers.get(run_id, set()))

        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Remove stale / blocked queue to protect event loop
                pass
