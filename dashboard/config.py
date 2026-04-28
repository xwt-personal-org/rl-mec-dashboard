"""Dashboard CLI and runtime configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DashboardConfig:
    logs_dir: Path
    benchmark_json: Path
    runs_dir: Path | None
    host: str
    port: int
    scan_interval_sec: float
    stall_threshold_sec: int
    recent_log_limit: int
    sse_interval_sec: float


def create_default_config() -> DashboardConfig:
    return DashboardConfig(
        logs_dir=Path("logs"),
        benchmark_json=Path("results/benchmark.json"),
        runs_dir=None,
        host="127.0.0.1",
        port=8088,
        scan_interval_sec=1.0,
        stall_threshold_sec=120,
        recent_log_limit=100,
        sse_interval_sec=1.0,
    )


def parse_cli_args(argv: list[str] | None = None) -> DashboardConfig:
    defaults = create_default_config()
    parser = argparse.ArgumentParser(description="RL-MEC Dashboard Server")
    parser.add_argument("--logs-dir", type=Path, default=defaults.logs_dir, help="Log directory path")
    parser.add_argument("--benchmark-json", type=Path, default=defaults.benchmark_json, help="Benchmark JSON path")
    parser.add_argument("--runs-dir", type=Path, default=defaults.runs_dir, help="Structured runs directory path")
    parser.add_argument("--host", type=str, default=defaults.host, help="Host to bind")
    parser.add_argument("--port", type=int, default=defaults.port, help="Port to bind")
    parser.add_argument("--scan-interval", type=float, default=defaults.scan_interval_sec, help="Scan interval seconds")
    parser.add_argument("--stall-threshold", type=int, default=defaults.stall_threshold_sec, help="Stall threshold seconds")
    parser.add_argument("--recent-log-limit", type=int, default=defaults.recent_log_limit, help="Recent log entry limit")
    parser.add_argument("--sse-interval", type=float, default=defaults.sse_interval_sec, help="SSE interval seconds")
    args = parser.parse_args(argv)
    return DashboardConfig(
        logs_dir=args.logs_dir,
        benchmark_json=args.benchmark_json,
        runs_dir=args.runs_dir,
        host=args.host,
        port=args.port,
        scan_interval_sec=args.scan_interval,
        stall_threshold_sec=args.stall_threshold,
        recent_log_limit=args.recent_log_limit,
        sse_interval_sec=args.sse_interval,
    )
