#!/usr/bin/env python3
"""
Dashboard Server — 轻看板服务 (FastAPI + SSE)
实时监控 RL-MEC Benchmark 训练状态

用法:
    python serve_dashboard.py --logs-dir logs --host 127.0.0.1 --port 8088
"""

# Compatibility note:
# This file remains the CLI entrypoint. Core implementation is gradually
# moved into the dashboard package while preserving existing commands.

from dashboard.api import create_app
from dashboard.config import parse_cli_args
from dashboard.log_parser import (
    classify_log_line,
    parse_algo_switch,
    parse_algorithm_count_from_summary,
    parse_benchmark_summary,
    parse_elapsed_from_tqdm,
    parse_env_from_algo_header,
    parse_eta_from_tqdm,
    parse_result,
    parse_step_from_tqdm,
    parse_update_count,
    strip_log_prefix,
)

config = parse_cli_args(None if __name__ == "__main__" else [])
app = create_app(config)

__all__ = [
    "app",
    "classify_log_line",
    "parse_algo_switch",
    "parse_algorithm_count_from_summary",
    "parse_benchmark_summary",
    "parse_elapsed_from_tqdm",
    "parse_env_from_algo_header",
    "parse_eta_from_tqdm",
    "parse_result",
    "parse_step_from_tqdm",
    "parse_update_count",
    "strip_log_prefix",
]


if __name__ == "__main__":
    import uvicorn

    print(f"experiments_dir={config.experiments_dir}")
    print(f"results_dir={config.results_dir}")
    print(f"logs_dir={config.logs_dir}")
    print(f"benchmark_json={config.benchmark_json}")
    uvicorn.run(app, host=config.host, port=config.port)
