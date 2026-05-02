"""FastAPI application and route definitions for the dashboard."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from dashboard.config import DashboardConfig, backup_scan_roots, benchmark_export_path
from dashboard.delete_service import (
    DeleteBlocked,
    DeleteTargetNotFound,
    DeleteTokenMismatch,
    LocalDataDeleteService,
)
from dashboard.experiment_reader import read_text_tail, safe_read_json_file
from dashboard.exporter import results_to_csv, results_to_markdown
from dashboard.models import RunDescriptor, RunState, dataclass_to_dict, run_state_to_dict, run_summary_to_dict
from dashboard.run_discovery import (
    discover_archive_only_backups,
    discover_experiment_backups_from_roots,
    enrich_backup_figures,
    infer_backup_metadata_from_dir,
    load_benchmark_results,
)
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

    @app.get("/api/backups/diagnostics")
    async def backup_diagnostics():
        return _backup_diagnostics(store)

    @app.get("/api/backups/{backup_id}")
    async def get_backup(backup_id: str):
        backup = _find_backup(store, backup_id)
        if backup is None:
            raise HTTPException(status_code=404, detail="Backup not found")
        return run_state_to_dict(_backup_state(store, backup))

    @app.get("/api/backups/{backup_id}/logs/{algorithm}/stdout")
    async def get_backup_stdout_log(backup_id: str, algorithm: str):
        return _backup_log_tail_payload(store, backup_id, algorithm, "stdout")

    @app.get("/api/backups/{backup_id}/logs/{algorithm}/stderr")
    async def get_backup_stderr_log(backup_id: str, algorithm: str):
        return _backup_log_tail_payload(store, backup_id, algorithm, "stderr")

    @app.get("/api/runs/{run_id}/backups")
    async def list_run_backups(run_id: str):
        backups = [backup for backup in _discover_backups(store) if backup.source_run_id == run_id]
        return {"run_id": run_id, "backups": [dataclass_to_dict(backup) for backup in backups]}

    @app.get("/api/delete-targets")
    async def list_delete_targets():
        service = LocalDataDeleteService(store.config)
        return {"targets": [dataclass_to_dict(target) for target in service.list_targets()]}

    @app.post("/api/delete-preview")
    async def delete_preview(payload: dict):
        target_id = str(payload.get("target_id") or "")
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id is required")
        service = LocalDataDeleteService(store.config)
        try:
            return dataclass_to_dict(service.preview_delete(target_id))
        except DeleteTargetNotFound as exc:
            raise HTTPException(status_code=404, detail="Delete target not found") from exc

    @app.post("/api/delete-confirm")
    async def delete_confirm(payload: dict):
        target_id = str(payload.get("target_id") or "")
        confirm_token = str(payload.get("confirm_token") or "")
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id is required")
        service = LocalDataDeleteService(store.config)
        try:
            result = service.confirm_delete(target_id, confirm_token)
        except DeleteTargetNotFound as exc:
            raise HTTPException(status_code=404, detail="Delete target not found") from exc
        except DeleteTokenMismatch as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except DeleteBlocked as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        store.scan_all_once()
        return dataclass_to_dict(result)

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
    roots = backup_scan_roots(store.config)
    backups = discover_experiment_backups_from_roots(roots, store.config.results_dir)
    archive_only = discover_archive_only_backups(store.config.results_dir)
    merged = _merge_backup_snapshots(backups, archive_only)
    return enrich_backup_figures(merged, store.config.figures_dir)


def _merge_backup_snapshots(backups, archive_only):
    merged = list(backups)
    existing_keys = {(backup.source_run_id, backup.timestamp) for backup in merged}
    existing_timestamps = {backup.timestamp for backup in merged}
    for backup in archive_only:
        if (backup.source_run_id, backup.timestamp) in existing_keys:
            continue
        if not backup.source_run_id and backup.timestamp in existing_timestamps:
            continue
        merged.append(backup)
    return sorted(merged, key=lambda item: (-int("".join(ch for ch in item.timestamp if ch.isdigit()) or "0"), item.backup_id))


def _find_backup(store: DashboardStateStore, backup_id: str):
    for backup in _discover_backups(store):
        if backup.backup_id == backup_id or backup.run_id == backup_id:
            return backup
    return None


def _backup_state(store: DashboardStateStore, backup) -> RunState:
    if backup.experiment_dir:
        experiment_dir = Path(backup.experiment_dir)
        descriptor = RunDescriptor(
            run_id=backup.backup_id,
            source_type="backup",
            mtime=experiment_dir.stat().st_mtime if experiment_dir.exists() else time.time(),
            display_name=backup.display_name or backup.backup_id,
            experiment_dir=experiment_dir,
            run_json_file=experiment_dir / "run.json",
            state_json_file=experiment_dir / "state.json",
            process_json_file=experiment_dir / "process.json",
            benchmark_export_file=_first_backup_benchmark_file(backup),
        )
        aggregator = RunStateAggregator(store.config)
        state = aggregator.initialize_state(descriptor)
        state = aggregator.scan_experiment_once(descriptor, state)
        state.run_id = backup.backup_id
        state.display_name = backup.display_name or state.display_name or backup.backup_id
        state.source_type = "backup"
        state.benchmark_export_path = backup.benchmark_archive_dir or state.benchmark_export_path
        archive_results = _load_backup_benchmark_results(backup)
        if archive_results:
            aggregator.merge_results(state, archive_results)
        _complete_state_from_results(state)
        return state

    results = _load_backup_benchmark_results(backup)
    updated_at = time.time()
    archive_dir = Path(backup.benchmark_archive_dir) if backup.benchmark_archive_dir else None
    if archive_dir is not None and archive_dir.exists():
        updated_at = archive_dir.stat().st_mtime
    state = RunState(
        run_id=backup.backup_id,
        display_name=backup.display_name or backup.backup_id,
        status="finished",
        source_type="archive",
        records=[],
        results=results,
        completed_algorithms=[result.algorithm for result in results],
        total_algorithms=len(results),
        progress_pct=100.0 if results else 0.0,
        overall_progress=float(len(results)),
        benchmark_export_path=backup.benchmark_archive_dir,
        updated_at=updated_at,
    )
    return state


def _first_backup_benchmark_file(backup) -> Path | None:
    if not backup.benchmark_archive_dir:
        return None
    archive_dir = Path(backup.benchmark_archive_dir)
    for name in backup.benchmark_files:
        path = archive_dir / name
        if path.exists():
            return path
    return None


def _load_backup_benchmark_results(backup):
    if not backup.benchmark_archive_dir:
        return []
    archive_dir = Path(backup.benchmark_archive_dir)
    results = []
    for name in backup.benchmark_files:
        path = archive_dir / name
        if not path.exists():
            continue
        try:
            results.extend(load_benchmark_results(path))
        except ValueError:
            continue
    return results


def _complete_state_from_results(state: RunState) -> None:
    if state.completed_algorithms or not state.results:
        return
    state.completed_algorithms = [result.algorithm for result in state.results if getattr(result, "algorithm", "")]
    if state.total_algorithms == 0:
        state.total_algorithms = len(state.completed_algorithms)
    if state.total_algorithms:
        state.progress_pct = round(len(state.completed_algorithms) / state.total_algorithms * 100, 2)
        state.overall_progress = float(len(state.completed_algorithms))


def _backup_diagnostics(store: DashboardStateStore) -> dict:
    config = store.config
    roots = backup_scan_roots(config)
    notes: list[str] = []
    scanned_roots = []
    for root in roots:
        info = {"path": str(root), "exists": False, "entries": 0, "candidate_backups": 0}
        try:
            root_path = Path(root)
            info["exists"] = root_path.exists() and root_path.is_dir()
            if info["exists"]:
                entries = [item for item in root_path.iterdir()]
                info["entries"] = len(entries)
                info["candidate_backups"] = sum(
                    1 for item in entries if item.is_dir() and infer_backup_metadata_from_dir(item) is not None
                )
        except Exception as exc:
            notes.append(f"scan root failed: {root}: {exc}")
        scanned_roots.append(info)

    archive_root = Path(config.results_dir) / "archive"
    archive_info = {"path": str(archive_root), "exists": False, "entries": 0, "benchmark_archives": 0}
    try:
        archive_info["exists"] = archive_root.exists() and archive_root.is_dir()
        if archive_info["exists"]:
            entries = [item for item in archive_root.iterdir()]
            archive_info["entries"] = len(entries)
            archive_info["benchmark_archives"] = sum(
                1 for item in entries if item.is_dir() and any(item.glob("benchmark*.json"))
            )
    except Exception as exc:
        notes.append(f"results archive scan failed: {archive_root}: {exc}")

    try:
        matched_backups = len(_discover_backups(store))
    except Exception as exc:
        matched_backups = 0
        notes.append(f"backup discovery failed: {exc}")

    return {
        "experiments_dir": str(config.experiments_dir or ""),
        "results_dir": str(config.results_dir),
        "figures_dir": str(config.figures_dir or ""),
        "backup_scan_dirs": [str(path) for path in config.backup_scan_dirs],
        "scanned_roots": scanned_roots,
        "results_archive": archive_info,
        "matched_backups": matched_backups,
        "notes": notes,
    }


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


def _backup_log_tail_payload(store: DashboardStateStore, backup_id: str, algorithm: str, stream: str) -> dict:
    backup = _find_backup(store, backup_id)
    if backup is None:
        raise HTTPException(status_code=404, detail="Backup not found")
    if not backup.experiment_dir:
        raise HTTPException(status_code=404, detail="Backup logs not found")
    state = _backup_state(store, backup)
    record = _find_record(state.records, algorithm)
    if record is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")
    path = _record_value(record, f"{stream}_path")
    text, exists = read_text_tail(Path(path), store.config.log_tail_bytes) if path else ("", False)
    return {
        "run_id": backup_id,
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
