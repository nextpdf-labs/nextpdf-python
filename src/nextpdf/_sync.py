"""Synchronous execution helper for running async coroutines safely."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine

_T = TypeVar("_T")


def run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine from synchronous code.

    Safe to call from environments with a running event loop (Jupyter, FastAPI
    background tasks, etc.) as well as plain synchronous scripts.

    When a running event loop is detected, the coroutine is dispatched to a
    new thread with its own event loop to avoid the ``RuntimeError`` raised
    by nested ``asyncio.run()`` calls.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Inside a running event loop — use a worker thread with its own loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    return asyncio.run(coro)
