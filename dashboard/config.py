"""Dashboard CLI and runtime configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DashboardConfig:
    logs_dir: Path = Path("logs")
    experiments_dir: Path | None = Path("experiments")
    results_dir: Path = Path("results")
    benchmark_json: Path = Path("results/benchmark.json")
    runs_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8088
    scan_interval_sec: float = 1.0
    stall_threshold_sec: int = 120
    recent_log_limit: int = 100
    sse_interval_sec: float = 1.0
    default_run_id: str = "paper2_full_17_vscode"
    quick_run_id: str = "vscode_quick"
    log_tail_bytes: int = 65536
    json_retry_keep_last: bool = True


def create_default_config() -> DashboardConfig:
    return DashboardConfig()


def benchmark_export_path(config: DashboardConfig, run_id: str) -> Path:
    return Path(config.results_dir) / f"benchmark_{run_id}.json"


def parse_cli_args(argv: list[str] | None = None) -> DashboardConfig:
    defaults = create_default_config()
    parser = argparse.ArgumentParser(description="RL-MEC Dashboard Server")
    parser.add_argument("--logs-dir", type=Path, default=defaults.logs_dir, help="Log directory path")
    parser.add_argument("--experiments-dir", type=Path, default=defaults.experiments_dir, help="paper2 experiments directory path")
    parser.add_argument("--results-dir", type=Path, default=defaults.results_dir, help="paper2 results directory path")
    parser.add_argument("--benchmark-json", type=Path, default=defaults.benchmark_json, help="Benchmark JSON path")
    parser.add_argument("--runs-dir", type=Path, default=defaults.runs_dir, help="Legacy structured runs directory path (deprecated)")
    parser.add_argument("--host", type=str, default=defaults.host, help="Host to bind")
    parser.add_argument("--port", type=int, default=defaults.port, help="Port to bind")
    parser.add_argument("--scan-interval", type=float, default=defaults.scan_interval_sec, help="Scan interval seconds")
    parser.add_argument("--stall-threshold", type=int, default=defaults.stall_threshold_sec, help="Stall threshold seconds")
    parser.add_argument("--recent-log-limit", type=int, default=defaults.recent_log_limit, help="Recent log entry limit")
    parser.add_argument("--sse-interval", type=float, default=defaults.sse_interval_sec, help="SSE interval seconds")
    parser.add_argument("--default-run-id", type=str, default=defaults.default_run_id, help="Default full benchmark run id")
    parser.add_argument("--quick-run-id", type=str, default=defaults.quick_run_id, help="Quick smoke test run id")
    parser.add_argument("--log-tail-bytes", type=int, default=defaults.log_tail_bytes, help="Maximum bytes returned by log tail APIs")
    args = parser.parse_args(argv)
    return DashboardConfig(
        logs_dir=args.logs_dir,
        experiments_dir=args.experiments_dir,
        results_dir=args.results_dir,
        benchmark_json=args.benchmark_json,
        runs_dir=args.runs_dir,
        host=args.host,
        port=args.port,
        scan_interval_sec=args.scan_interval,
        stall_threshold_sec=args.stall_threshold,
        recent_log_limit=args.recent_log_limit,
        sse_interval_sec=args.sse_interval,
        default_run_id=args.default_run_id,
        quick_run_id=args.quick_run_id,
        log_tail_bytes=args.log_tail_bytes,
        json_retry_keep_last=defaults.json_retry_keep_last,
    )
