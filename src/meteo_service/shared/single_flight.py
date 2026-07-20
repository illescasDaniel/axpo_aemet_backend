import asyncio
from collections.abc import Callable, Coroutine, Hashable
from typing import Any


class SingleFlight[T]:
    """If several callers ask for the same key at once, only one runs ``factory``; the others await that result."""

    def __init__(self):
        self._inflight: dict[Hashable, asyncio.Task[T]] = {}

    async def do(self, key: Hashable, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        if (task := self._inflight.get(key)) is None:
            task = asyncio.create_task(factory())
            self._inflight[key] = task
            task.add_done_callback(lambda _: self._inflight.pop(key, None))
        return await task
