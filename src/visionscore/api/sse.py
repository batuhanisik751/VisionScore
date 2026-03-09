from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from visionscore.pipeline.orchestrator import AnalysisOrchestrator


def format_sse(data: dict[str, Any], event: str | None = None) -> str:
    """Format a dict as an SSE text frame."""
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    return "\n".join(lines) + "\n\n"


class AnalysisProgressBridge:
    """Thread-safe bridge between the sync orchestrator and async SSE generator.

    The orchestrator runs in a worker thread via ``asyncio.to_thread``.  It
    calls *push* (thread-safe) to enqueue progress dicts.  The async SSE
    generator awaits *receive* to yield them to the client.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def push(self, event: dict[str, Any]) -> None:
        """Enqueue from the sync orchestrator thread."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    async def receive(self) -> dict[str, Any]:
        return await self._queue.get()

    def make_callback(self):  # noqa: ANN201
        """Return a progress_callback compatible with ``orchestrator.run()``."""

        def _cb(stage: str, index: int, total: int, message: str) -> None:
            self.push(
                {
                    "event": "progress",
                    "stage": stage,
                    "stage_index": index,
                    "total_stages": total,
                    "message": message,
                    "percent": round((index / total) * 100),
                }
            )

        return _cb


async def analysis_event_stream(
    orchestrator: AnalysisOrchestrator,
    image_path: Path,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE frames as the orchestrator runs."""

    bridge = AnalysisProgressBridge()
    bridge.set_loop(asyncio.get_running_loop())

    async def _run_in_thread() -> None:
        report = await asyncio.to_thread(
            orchestrator.run,
            image_path,
            progress_callback=bridge.make_callback(),
        )
        bridge.push(
            {
                "event": "complete",
                "report": json.loads(report.model_dump_json()),
                "warnings": orchestrator.warnings,
            }
        )

    task = asyncio.create_task(_run_in_thread())

    try:
        while True:
            evt = await bridge.receive()
            event_type = evt.pop("event", "message")
            yield format_sse(evt, event=event_type)
            if event_type in ("complete", "error"):
                break
    except asyncio.CancelledError:
        task.cancel()
        raise
    except Exception as exc:
        yield format_sse({"detail": str(exc)}, event="error")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
