import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pymongo.errors import AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError

T = TypeVar("T")


async def retry_mongo_write(operation: Callable[[], Awaitable[T]], attempts: int = 3) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(0.2 * (attempt + 1))
    if last_error is None:
        raise RuntimeError("Mongo write retry failed without an exception.")
    raise last_error
