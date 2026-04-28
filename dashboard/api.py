"""FastAPI application and route definitions for the dashboard."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from dashboard.config import DashboardConfig
from dashboard.exporter import results_to_csv, results_to_markdown
from dashboard.models import run_state_to_dict, run_summary_to_dict
from dashboard.sse import create_sse_response, run_snapshot_event_generator
from dashboard.state_aggregator import RunStateAggregator
from dashboard.state_store import DashboardStateStore


def create_app(config: DashboardConfig) -> FastAPI:
    app = FastAPI(title="RL-MEC Dashboard")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = DashboardStateStore(config, RunStateAggregator(config))
    app.state.config = config
    app.state.store = store
    register_routes(app, store)

    @app.on_event("startup")
    async def _startup() -> None:
        store.scan_all_once()
        store.start_background_scan()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        store.shutdown()

    return app


def register_routes(app: FastAPI, store: DashboardStateStore) -> None:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        html_path = Path(__file__).resolve().parent.parent / "monitor_dashboard.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8", errors="replace"))
        raise HTTPException(status_code=404, detail="Dashboard not found")

    @app.get("/api/health")
    async def health():
        runs = store.get_runs()
        return {
            "status": "ok",
            "version": "0.2.0",
            "has_structured_protocol": any(run.source_type in ("structured", "mixed") for run in runs),
            "run_count": len(runs),
        }

    @app.get("/api/runs")
    async def list_runs():
        return {"runs": [run_summary_to_dict(summary) for summary in store.get_runs()]}

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        state = store.get_run_state(run_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run_state_to_dict(state)

    @app.get("/api/runs/{run_id}/events")
    async def stream_events(run_id: str, request: Request):
        if store.get_run_state(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        generator = run_snapshot_event_generator(run_id, request, store, store.config.sse_interval_sec)
        return create_sse_response(generator)

    @app.get("/api/compare")
    async def compare(run_ids: str = "", metric: str = "reward"):
        try:
            return store.get_compare_payload(_parse_run_ids(run_ids), metric)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/export/results.csv")
    async def export_csv(run_ids: str = ""):
        content = results_to_csv(_selected_states(store, run_ids))
        return Response(content=content, media_type="text/csv")

    @app.get("/api/export/results.md")
    async def export_markdown(run_ids: str = ""):
        content = results_to_markdown(_selected_states(store, run_ids))
        return Response(content=content, media_type="text/markdown")

    @app.post("/api/shutdown")
    async def shutdown():
        store.shutdown()

        def _delayed_exit() -> None:
            time.sleep(1)
            os._exit(0)

        threading.Thread(target=_delayed_exit, daemon=True).start()
        return {"message": "Shutting down dashboard server..."}


def _parse_run_ids(run_ids: str) -> list[str]:
    return [item.strip() for item in run_ids.split(",") if item.strip()]


def _selected_states(store: DashboardStateStore, run_ids: str):
    selected_ids = _parse_run_ids(run_ids)
    if not selected_ids:
        selected_ids = [summary.run_id for summary in store.get_runs()]
    states = []
    for run_id in selected_ids:
        state = store.get_run_state(run_id)
        if state is not None:
            states.append(state)
    return states
