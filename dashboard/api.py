"""FastAPI application and route definitions for the dashboard."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from dashboard.config import DashboardConfig, benchmark_export_path
from dashboard.experiment_reader import read_text_tail, safe_read_json_file
from dashboard.exporter import results_to_csv, results_to_markdown
from dashboard.models import dataclass_to_dict, run_state_to_dict, run_summary_to_dict
from dashboard.run_discovery import discover_experiment_backups, enrich_backup_figures
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
            "version": "0.3.0",
            "has_experiment_state": any(run.source_type == "experiment_state" for run in runs),
            "has_structured_protocol": any(run.source_type in ("legacy_structured", "structured", "mixed") for run in runs),
            "run_count": len(runs),
            "default_run_id": store.config.default_run_id,
            "quick_run_id": store.config.quick_run_id,
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

    @app.get("/api/backups")
    async def list_backups():
        backups = _discover_backups(store)
        return {"backups": [dataclass_to_dict(backup) for backup in backups]}

    @app.get("/api/runs/{run_id}/backups")
    async def list_run_backups(run_id: str):
        backups = [backup for backup in _discover_backups(store) if backup.source_run_id == run_id]
        return {"run_id": run_id, "backups": [dataclass_to_dict(backup) for backup in backups]}

    @app.get("/api/runs/{run_id}/events")
    async def stream_events(run_id: str, request: Request):
        if store.get_run_state(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        generator = run_snapshot_event_generator(run_id, request, store, store.config.sse_interval_sec)
        return create_sse_response(generator)

    @app.get("/api/runs/{run_id}/logs/{algorithm}/stdout")
    async def get_stdout_log(run_id: str, algorithm: str):
        return _log_tail_payload(store, run_id, algorithm, "stdout")

    @app.get("/api/runs/{run_id}/logs/{algorithm}/stderr")
    async def get_stderr_log(run_id: str, algorithm: str):
        return _log_tail_payload(store, run_id, algorithm, "stderr")

    @app.get("/api/runs/{run_id}/benchmark")
    async def get_benchmark_export(run_id: str):
        path = benchmark_export_path(store.config, run_id)
        payload, error = safe_read_json_file(path)
        if payload is None and error is None:
            return {"run_id": run_id, "exists": False, "results": []}
        if error:
            return {"run_id": run_id, "exists": True, "transient_error": error, "results": []}
        if isinstance(payload, list):
            return {"run_id": run_id, "exists": True, "results": payload}
        return {
            "run_id": run_id,
            "exists": True,
            "transient_error": f"invalid json file: {path}",
            "results": [],
        }

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


def _discover_backups(store: DashboardStateStore):
    backups = discover_experiment_backups(store.config.experiments_dir, store.config.results_dir)
    return enrich_backup_figures(backups, store.config.figures_dir)


def _log_tail_payload(store: DashboardStateStore, run_id: str, algorithm: str, stream: str) -> dict:
    state = store.get_run_state(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    record = _find_record(state.records, algorithm)
    if record is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    path = _record_value(record, f"{stream}_path")
    text, exists = read_text_tail(Path(path), store.config.log_tail_bytes) if path else ("", False)
    return {
        "run_id": run_id,
        "algorithm": algorithm,
        "stream": stream,
        "path": path,
        "exists": exists,
        "text": text,
    }


def _find_record(records, algorithm: str):
    for record in records:
        if _record_value(record, "name") == algorithm:
            return record
    return None


def _record_value(record, key: str):
    if isinstance(record, dict):
        return record.get(key, "")
    return getattr(record, key, "")
