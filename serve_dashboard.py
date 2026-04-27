#!/usr/bin/env python3
"""
Dashboard Server — 轻看板服务 (FastAPI + SSE)
实时监控 RL-MEC Benchmark 训练状态

用法:
    python serve_dashboard.py --logs-dir logs --host 127.0.0.1 --port 8088
"""

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional
import threading
from datetime import datetime

# Optional: provide a lightweight fallback if FastAPI is not installed in the env
try:
    from fastapi import FastAPI, HTTPException, Request  # type: ignore
    from fastapi.responses import HTMLResponse, StreamingResponse  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False
    class _DummyApp:
        def get(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
        def on_event(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    app = _DummyApp()
    class HTMLResponse:  # type: ignore
        pass
    class StreamingResponse:  # type: ignore
        pass
    class HTTPException(Exception):  # type: ignore
        pass
    class Request:  # type: ignore
        pass
    class CORSMiddleware:  # type: ignore
        pass

if FASTAPI_AVAILABLE:
    app = FastAPI(title="RL-MEC Dashboard")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # In fallback mode, the dummy app will ignore middleware
    pass

LOG_DIR = Path("logs")
BENCHMARK_JSON = Path("results/benchmark.json")
HOST = "127.0.0.1"
PORT = 8088

STALL_THRESHOLD_SEC = 120
SCAN_INTERVAL = 1.0

_run_states: dict[str, "RunState"] = {}
_state_lock = threading.Lock()
_log_dir_ref: Path = LOG_DIR
_json_ref: Path = BENCHMARK_JSON

_benchmark_json_cache: dict[str, tuple[float, list[dict]]] = {}


class RunState:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.status = "idle"
        self.current_algorithm = ""
        self.current_step = 0
        self.total_step = 500000
        self.progress_pct = 0.0
        self.it_per_sec = 0.0
        self.eta_seconds = 0
        self.elapsed_seconds = 0
        self.update_count = 0
        self.completed_algorithms: list[str] = []
        self.log_results: list[dict] = []
        self.historical_results: list[dict] = []
        self.results: list[dict] = []
        self.last_error = ""
        self.updated_at = time.time()
        self.log_offsets: dict[str, int] = {}
        self.last_log_time = time.time()
        self.process_alive = False
        self.recent_logs: list[dict] = []
        self.overall_progress = 0
        self.degraded = False
        self.total_algorithms = 17
        self.stderr_file = ""
        self.stdout_file = ""

    def _merge_results(self) -> list[dict]:
        merged = []
        log_algos = {r["algorithm"] for r in self.log_results}
        for r in self.log_results:
            merged.append({**r, "source": "current_run"})
        for r in self.historical_results:
            if r["algorithm"] not in log_algos:
                merged.append({**r, "source": "historical"})
        merged.sort(key=lambda x: x.get("train_time", 0) if x.get("train_time") else 0)
        return merged

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "current_algorithm": self.current_algorithm,
            "current_step": self.current_step,
            "total_step": self.total_step,
            "progress_pct": self.progress_pct,
            "it_per_sec": self.it_per_sec,
            "eta_seconds": self.eta_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "update_count": self.update_count,
            "completed_algorithms": self.completed_algorithms,
            "results": self._merge_results(),
            "last_error": self.last_error,
            "updated_at": self.updated_at,
            "process_alive": self.process_alive,
            "recent_logs": self.recent_logs[-50:],
            "overall_progress": self.overall_progress,
            "degraded": self.degraded,
            "total_algorithms": self.total_algorithms,
            "stderr_file": self.stderr_file,
            "stdout_file": self.stdout_file,
        }


def discover_runs(log_dir: Path) -> dict[str, dict]:
    runs = {}
    if not log_dir.exists():
        return runs
    for f in sorted(log_dir.glob("benchmark*.log")):
        base = f.stem
        if base.endswith(".err"):
            continue
        err_counterpart = f.parent / (base + ".err.log")
        run_id = base.replace("benchmark_", "").replace("full_", "")
        has_err = err_counterpart.exists()
        runs[run_id] = {
            "id": run_id,
            "stdout": str(f),
            "stderr": str(err_counterpart) if has_err else str(f),
            "mtime": f.stat().st_mtime,
        }
    return runs


def is_run_process_alive(state: RunState) -> bool:
    """Check if a specific run's log files have been modified recently."""
    now = time.time()
    for filepath in (state.stderr_file, state.stdout_file):
        if filepath:
            p = Path(filepath)
            if p.exists() and (now - p.stat().st_mtime) < 30:
                return True
    return False


def parse_step_from_tqdm(line: str) -> Optional[tuple]:
    content = strip_log_prefix(line)
    m = re.search(
        r"Training\s+(\w+Agent):\s+\d+%\|[^|]*\|\s+(\d+)/(\d+)\s+\[[^]]*,\s+([\d.]+)it/s",
        content,
    )
    if m:
        return int(m.group(2)), int(m.group(3)), float(m.group(4))

    m2 = re.search(r"Training\s+\w+Agent:\s+\d+%.*?(\d+)/(\d+).*?([\d.]+)\s*it/s", content)
    if m2:
        return int(m2.group(1)), int(m2.group(2)), float(m2.group(3))

    m3 = re.search(r"Training\s+\w+Agent:\s+(\d+)it\s+\[([^]]+),\s+([\d.]+)it/s", content)
    if m3:
        elapsed_str = m3.group(2)
        h = m = s = 0
        hm = re.match(r"(\d+):(\d+):(\d+)", elapsed_str)
        if hm:
            h, m, s = int(hm.group(1)), int(hm.group(2)), int(hm.group(3))
        else:
            sm = re.match(r"(\d+):(\d+)", elapsed_str)
            if sm:
                m, s = int(sm.group(1)), int(sm.group(2))
            else:
                sm2 = re.match(r"(\d+)s", elapsed_str)
                if sm2:
                    s = int(sm2.group(1))
        return int(m3.group(1)), 0, float(m3.group(3))

    return None


def parse_elapsed_from_tqdm(line: str) -> float:
    content = strip_log_prefix(line)
    m = re.search(r"\[(\d+):(\d+):(\d+)<", content)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m2 = re.search(r"\[(\d+):(\d+)<", content)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    return 0.0


def parse_eta_from_tqdm(line: str) -> int:
    content = strip_log_prefix(line)
    m = re.search(r"<(\d+):(\d+):(\d+)", content)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m2 = re.search(r"<(\d+):(\d+)", content)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    m3 = re.search(r"<(\d+)s", content)
    if m3:
        return int(m3.group(1))
    return 0


def strip_log_prefix(line: str) -> str:
    m = re.search(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+\s+-\s+\w+\s+-\s+(.*)$", line)
    return m.group(1) if m else line


def parse_algo_switch(line: str) -> Optional[str]:
    content = strip_log_prefix(line)
    m = re.search(r"Algorithm:\s*(\w+)", content, re.IGNORECASE)
    return m.group(1) if m else None


def parse_result(line: str) -> Optional[dict]:
    content = strip_log_prefix(line)
    m = re.search(r"\[(\w+)\]\s+reward=([-\d.]+)\+/-([-\d.]+)\s+time=([\d.]+)s", content, re.IGNORECASE)
    if m:
        return {
            "algorithm": m.group(1),
            "reward": float(m.group(2)),
            "reward_std": float(m.group(3)),
            "train_time": float(m.group(4)),
            "source": "log",
            "deadline_miss_rate": None,
            "throughput": None,
            "comm_score": None,
            "update_count": None,
        }
    m2 = re.search(r"\[(\w+)\].*?reward=([-\d.]+).*?time=([\d.]+)s", content, re.IGNORECASE)
    if m2:
        return {
            "algorithm": m2.group(1),
            "reward": float(m2.group(2)),
            "reward_std": 0,
            "train_time": float(m2.group(3)),
            "source": "log",
            "deadline_miss_rate": None,
            "throughput": None,
            "comm_score": None,
            "update_count": None,
        }
    return None


def parse_update_count(line: str) -> Optional[int]:
    content = strip_log_prefix(line)
    m = re.search(r"update_count=([\d.]+)", content, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    return None


def parse_env_from_algo_header(line: str) -> Optional[str]:
    content = strip_log_prefix(line)
    m = re.search(r"Env:\s*(\S+)", content, re.IGNORECASE)
    return m.group(1) if m else None


def parse_benchmark_summary(line: str) -> bool:
    return "ALL ALGORITHMS COMPLETE" in line or "Benchmark finished" in line


def parse_algorithm_count_from_summary(line: str) -> Optional[int]:
    """Extract total algorithm count from BENCHMARK header line.
    Matches: BENCHMARK -- Some Description (17 algorithms)
    """
    content = strip_log_prefix(line)
    m = re.search(r"BENCHMARK\s+--\s+.*?\((\d+)\s+algorithms?\)", content, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def classify_log_line(line: str) -> Optional[str]:
    # Use word-boundary aware matching to avoid false positives.
    lower = line.lower()
    if __import__('re').search(r"\b(error|exception|traceback|failed)\b", lower):
        return "error"
    if __import__('re').search(r"\b(warning|warn)\b", lower):
        return "warn"
    if __import__('re').search(r"algorithm:", lower) or __import__('re').search(r"\breward=", lower) or __import__('re').search(r"\bbenchmark\b", lower) or __import__('re').search(r"\bfinished\b", lower) or __import__('re').search(r"\bcomplete\b", lower):
        return "info"
    return None


def load_benchmark_json(json_path: Path, state: RunState):
    if not json_path.exists():
        return
    try:
        cache_key = str(json_path.resolve())
        mtime = json_path.stat().st_mtime

        if cache_key in _benchmark_json_cache and _benchmark_json_cache[cache_key][0] == mtime:
            historical_results = _benchmark_json_cache[cache_key][1]
        else:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return

            json_lookup = {}
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                algo = entry.get("algorithm", "")
                if algo:
                    json_lookup[algo] = entry

            historical_results = []
            for algo, entry in json_lookup.items():
                historical_results.append({
                    "algorithm": algo,
                    "reward": entry.get("final_reward_mean_mean", 0),
                    "reward_std": entry.get("final_reward_mean_std", 0),
                    "train_time": entry.get("train_time_seconds_mean", 0),
                    "latency": entry.get("final_latency_mean_mean"),
                    "energy": entry.get("final_energy_mean_mean"),
                    "deadline_miss_rate": entry.get("final_deadline_miss_rate_mean"),
                    "throughput": entry.get("final_throughput_tasks_per_step_mean"),
                    "comm_score": entry.get("final_comm_score_mean"),
                    "update_count": entry.get("total_updates_mean"),
                    "environment": entry.get("environment", ""),
                })
            _benchmark_json_cache[cache_key] = (mtime, historical_results)

        log_algos = {r["algorithm"] for r in state.log_results}

        # Build lookup from all historical entries before filtering
        json_lookup = {}
        for h in historical_results:
            json_lookup[h["algorithm"]] = h

        state.historical_results = [
            h for h in historical_results if h["algorithm"] not in log_algos
        ]

        # Backfill missing fields in log_results from json_lookup
        for r in state.log_results:
            if r.get("algorithm") in json_lookup:
                entry = json_lookup[r["algorithm"]]
                keys_to_backfill = ["latency", "energy", "deadline_miss_rate", "throughput", "comm_score", "update_count"]
                for key in keys_to_backfill:
                    if r.get(key) is None and entry.get(key) is not None:
                        r[key] = entry[key]
                if not r.get("environment") and entry.get("environment"):
                    r["environment"] = entry["environment"]
    except Exception as e:
        state.last_error = f"Failed to load benchmark.json: {e}"
        state.degraded = True


def scan_log_file(filepath: str, state: RunState, is_stderr: bool):
    if not filepath or not Path(filepath).exists():
        state.log_offsets.pop(filepath, None)
        return
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(state.log_offsets.get(filepath, 0))
            for line in f:
                step_info = parse_step_from_tqdm(line)
                if step_info:
                    cur, tot, ips = step_info
                    state.current_step = cur
                    if tot > 0:
                        state.total_step = tot
                    state.it_per_sec = ips
                    if ips > 0 and tot > 0:
                        remaining = tot - cur
                        state.eta_seconds = int(remaining / ips)
                    state.last_log_time = time.time()

                eta = parse_eta_from_tqdm(line)
                if eta > 0:
                    state.eta_seconds = eta

                elapsed = parse_elapsed_from_tqdm(line)
                if elapsed > 0:
                    state.elapsed_seconds = elapsed

                uc = parse_update_count(line)
                if uc is not None:
                    state.update_count = uc

                result = parse_result(line)
                if result:
                    existing = [r for r in state.log_results if r.get("algorithm") == result["algorithm"]]
                    if not existing:
                        state.log_results.append(result)
                    if result["algorithm"] not in state.completed_algorithms:
                        state.completed_algorithms.append(result["algorithm"])

                env_name = parse_env_from_algo_header(line)
                if env_name and state.current_algorithm:
                    for r in state.log_results:
                        if r.get("algorithm") == state.current_algorithm and not r.get("environment"):
                            r["environment"] = env_name

                if parse_benchmark_summary(line):
                    if state.current_algorithm and state.current_algorithm not in state.completed_algorithms:
                        state.completed_algorithms.append(state.current_algorithm)
                    state.status = "finished"

                algo_count = parse_algorithm_count_from_summary(line)
                if algo_count and algo_count > state.total_algorithms:
                    state.total_algorithms = algo_count

                algo = parse_algo_switch(line)
                if algo:
                    if state.current_algorithm and state.current_algorithm != algo:
                        if state.current_algorithm not in state.completed_algorithms:
                            state.completed_algorithms.append(state.current_algorithm)
                    state.current_algorithm = algo
                    state.last_log_time = time.time()
                    # Heuristic baselines expand total algorithm count
                    if algo in ("Greedy", "Random", "Local-only", "Full-offload"):
                        state.total_algorithms = max(state.total_algorithms, 21)

                log_type = classify_log_line(line)
                if log_type:
                    state.recent_logs.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "level": log_type,
                        "text": line.strip()[:300],
                    })
                    if len(state.recent_logs) > 100:
                        state.recent_logs = state.recent_logs[-100:]

            state.log_offsets[filepath] = f.tell()
    except Exception as e:
        state.last_error = f"Parse error ({Path(filepath).name}): {e}"
        state.degraded = True


def scan_logs(log_dir: Path, state: RunState):
    if not log_dir.exists():
        return

    # F: Log file rotation — always check for newer runs
    runs = discover_runs(log_dir)
    if runs:
        latest = max(runs.values(), key=lambda x: x["mtime"])
        latest_mtime = latest.get("mtime", 0)
        new_stderr = latest.get("stderr", "")
        new_stdout = latest.get("stdout", "")

        if not state.stderr_file and not state.stdout_file:
            # First assignment
            state.stderr_file = new_stderr
            state.stdout_file = new_stdout
        elif (new_stderr and new_stderr != state.stderr_file) or (new_stdout and new_stdout != state.stdout_file):
            # Newer run exists — switch if current run is done/stalled/idle or new file is fresh
            now = time.time()
            state_done = state.status == "stalled"
            new_file_fresh = latest_mtime > state.last_log_time + 5
            if state_done or new_file_fresh:
                state.stderr_file = new_stderr
                state.stdout_file = new_stdout
                state.log_offsets.clear()
                # Reset state fields to idle defaults
                state.status = "idle"
                state.current_algorithm = ""
                state.current_step = 0
                state.total_step = 500000
                state.progress_pct = 0.0
                state.it_per_sec = 0.0
                state.eta_seconds = 0
                state.elapsed_seconds = 0
                state.update_count = 0
                state.completed_algorithms = []
                state.log_results = []
                state.last_error = ""
                state.last_log_time = time.time()
                state.recent_logs = []
                state.overall_progress = 0
                state.degraded = False

    stderr_file = state.stderr_file
    stdout_file = state.stdout_file

    # D2: Clean up offsets for files no longer tracked
    tracked = {stderr_file, stdout_file}
    stale_offsets = [fp for fp in state.log_offsets if fp not in tracked]
    for fp in stale_offsets:
        state.log_offsets.pop(fp, None)

    scan_log_file(stderr_file, state, is_stderr=True)
    scan_log_file(stdout_file, state, is_stderr=False)

    now = time.time()
    if state.current_step > 0 and state.total_step > 0:
        state.progress_pct = round(state.current_step / state.total_step * 100, 2)

    state.process_alive = is_run_process_alive(state)

    n_completed = len(state.completed_algorithms)
    current_frac = 0.0
    if state.current_step > 0 and state.total_step > 0 and state.status != "finished":
        current_frac = state.current_step / state.total_step
    state.overall_progress = n_completed + round(current_frac, 2)

    if state.status == "finished":
        pass
    elif n_completed >= state.total_algorithms:
        state.status = "finished"
    elif not state.process_alive and state.current_step > 0:
        if state.current_step >= state.total_step and state.current_algorithm in state.completed_algorithms:
            state.status = "finished"
        elif now - state.last_log_time > STALL_THRESHOLD_SEC:
            state.status = "stalled"
        else:
            state.status = "running"
    elif state.current_step >= state.total_step and state.total_step > 0 and state.current_step > 0:
        state.status = "running"
    elif now - state.last_log_time > STALL_THRESHOLD_SEC and state.current_step > 0:
        state.status = "stalled"
    elif state.current_step > 0:
        state.status = "running"
    else:
        state.status = "idle"

    if state.degraded and state.status not in ("finished",):
        state.status = "degraded"

    state.updated_at = time.time()


def background_scan(log_dir: Path, json_path: Path, interval: float = SCAN_INTERVAL):
    def loop():
        while True:
            with _state_lock:
                for run_id, state in _run_states.items():
                    scan_logs(log_dir, state)
                    load_benchmark_json(json_path, state)
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "monitor_dashboard.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/api/runs")
async def list_runs():
    runs_info = discover_runs(_log_dir_ref)
    result = []
    for rid, info in runs_info.items():
        result.append({
            "run_id": rid,
            "stdout": info["stdout"],
            "stderr": info["stderr"],
            "mtime": info["mtime"],
        })
    result.sort(key=lambda x: x["mtime"], reverse=True)
    with _state_lock:
        for r in result:
            if r["run_id"] not in _run_states:
                state = RunState(r["run_id"])
                state.stdout_file = r["stdout"]
                state.stderr_file = r["stderr"]
                load_benchmark_json(_json_ref, state)
                _run_states[r["run_id"]] = state
    return {"runs": result}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    with _state_lock:
        if run_id not in _run_states:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_states[run_id].to_dict()


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    async def event_generator():
        import asyncio
        while True:
            if await request.is_disconnected():
                break
            with _state_lock:
                if run_id not in _run_states:
                    break
                snapshot = json.dumps(_run_states[run_id].to_dict(), sort_keys=True)
            yield f"event: snapshot\ndata: {snapshot}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/shutdown")
async def shutdown():
    def _delayed_exit():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_delayed_exit, daemon=True).start()
    return {"message": "Shutting down..."}


@app.on_event("startup")
async def startup():
    await list_runs()
    if _run_states:
        latest_id = max(_run_states.keys(), key=lambda k: _run_states[k].updated_at)
    else:
        latest_id = "latest"
        with _state_lock:
            _run_states[latest_id] = RunState(latest_id)
    background_scan(_log_dir_ref, _json_ref)


def parse_args():
    parser = argparse.ArgumentParser(description="RL-MEC Dashboard Server")
    parser.add_argument("--logs-dir", type=str, default="logs", help="Log directory path")
    parser.add_argument("--benchmark-json", type=str, default="results/benchmark.json", help="Benchmark JSON path")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8088, help="Port to bind")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    LOG_DIR = Path(args.logs_dir)
    BENCHMARK_JSON = Path(args.benchmark_json)
    HOST = args.host
    PORT = args.port
    _log_dir_ref = LOG_DIR
    _json_ref = BENCHMARK_JSON
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
