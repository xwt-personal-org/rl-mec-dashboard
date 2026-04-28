"""Server-Sent Events helpers for dashboard snapshots."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi.responses import StreamingResponse

from dashboard.models import run_state_to_dict
from dashboard.state_store import DashboardStateStore


async def run_snapshot_event_generator(
    run_id: str,
    request: Any,
    store: DashboardStateStore,
    interval_sec: float,
):
    while True:
        if await request.is_disconnected():
            break
        state = store.get_run_state(run_id)
        if state is None:
            break
        payload = json.dumps(run_state_to_dict(state), sort_keys=True)
        yield f"event: snapshot\ndata: {payload}\n\n"
        await asyncio.sleep(interval_sec)


def create_sse_response(generator):
    return StreamingResponse(generator, media_type="text/event-stream")
