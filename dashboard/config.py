"""Dashboard CLI and runtime configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


def _str_to_bool(value: bool | str) -> bool:
    """Parse boolean from string, supporting true/false/1/0/yes/no.

    Accepts both bool (passthrough for argparse defaults) and str input.
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


@dataclass
class DashboardConfig:
    logs_dir: Path = Path("logs")
    experiments_dir: Path | None = Path("experiments")
    results_dir: Path = Path("results")
    figures_dir: Path | None = Path("figures")
    backup_scan_dirs: list[Path] = field(default_factory=list)
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
    # M13: Mainline-A runtime configuration
    paper2_root: Path | None = None
    paper2_python: Path | None = None
    mainline_a_enabled: bool = True
    benchmark_scan_dirs: list[Path] = field(default_factory=list)
    benchmark_file_globs: list[str] = field(default_factory=lambda: ["benchmark*.json"])
    mainline_a_run_aliases: dict[str, str] = field(default_factory=dict)


def create_default_config() -> DashboardConfig:
    return DashboardConfig(
        mainline_a_run_aliases={
            "benchmark_direct_all_17_vscode": "Direct Full17 Benchmark",
            "paper2_full_17_vscode": "Paper2 Full17 Experiment",
            "vscode_quick": "VSCode Quick Benchmark",
        }
    )


def benchmark_export_path(config: DashboardConfig, run_id: str) -> Path:
    return Path(config.results_dir) / f"benchmark_{run_id}.json"


def backup_scan_roots(config: DashboardConfig) -> list[Path]:
    roots: list[Path] = []
    if config.experiments_dir is not None:
        roots.append(Path(config.experiments_dir))
    roots.extend(Path(path) for path in config.backup_scan_dirs)

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def paper2_runtime_roots(config: DashboardConfig) -> dict[str, Path | None]:
    """Return paper2 runtime directory mapping for inspection and debugging."""
    return {
        "paper2_root": config.paper2_root,
        "paper2_python": config.paper2_python,
        "experiments_dir": config.experiments_dir,
        "results_dir": config.results_dir,
        "figures_dir": config.figures_dir,
        "logs_dir": config.logs_dir,
    }


def benchmark_scan_roots(config: DashboardConfig) -> list[Path]:
    """Return deduplicated benchmark scan directories.

    Includes config.results_dir as baseline, then any additional
    benchmark_scan_dirs, with duplicates removed via resolved path.
    """
    roots_map: dict[str, Path] = {}
    if config.results_dir is not None:
        results = Path(config.results_dir)
        roots_map[str(results.resolve(strict=False)).lower()] = results
    for d in config.benchmark_scan_dirs:
        key = str(d.resolve(strict=False)).lower()
        if key not in roots_map:
            roots_map[key] = d
    return list(roots_map.values())


def parse_cli_args(argv: list[str] | None = None) -> DashboardConfig:
    defaults = create_default_config()
    parser = argparse.ArgumentParser(description="RL-MEC Dashboard Server")
    parser.add_argument("--logs-dir", type=Path, default=defaults.logs_dir, help="Log directory path")
    parser.add_argument("--experiments-dir", type=Path, default=defaults.experiments_dir, help="paper2 experiments directory path")
    parser.add_argument("--results-dir", type=Path, default=defaults.results_dir, help="paper2 results directory path")
    parser.add_argument("--figures-dir", type=Path, default=defaults.figures_dir, help="paper2 figures directory path")
    parser.add_argument(
        "--backup-scan-dir",
        type=Path,
        action="append",
        default=[],
        help="Additional directory to scan for experiment backups. Can be repeated.",
    )
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
    # M13: Mainline-A runtime CLI args
    parser.add_argument("--paper2-root", type=Path, default=None, help="paper2 project root directory")
    parser.add_argument("--paper2-python", type=Path, default=None, help="Python executable path for paper2 venv")
    parser.add_argument(
        "--mainline-a-enabled",
        type=_str_to_bool,
        default=True,
        help="Enable Mainline-A runtime (true/false/1/0)",
    )
    parser.add_argument(
        "--benchmark-scan-dir",
        type=Path,
        action="append",
        default=[],
        help="Additional benchmark scan directory. Can be repeated.",
    )
    parser.add_argument(
        "--benchmark-file-glob",
        type=str,
        action="append",
        default=None,
        help="Benchmark file glob pattern. Can be repeated.",
    )
    parser.add_argument(
        "--mainline-a-alias",
        type=str,
        action="append",
        default=None,
        help="Mainline-A run alias (key=value). Can be repeated.",
    )
    args = parser.parse_args(argv)

    paper2_root: Path | None = args.paper2_root

    # Derive sub-directories from paper2_root when set and not explicitly overridden.
    # We compare against defaults to detect "not explicitly provided by user".
    if paper2_root is not None:
        if args.experiments_dir == defaults.experiments_dir:
            args.experiments_dir = paper2_root / "experiments"
        if args.results_dir == defaults.results_dir:
            args.results_dir = paper2_root / "results"
        if args.figures_dir == defaults.figures_dir:
            args.figures_dir = paper2_root / "figures"
        if args.logs_dir == defaults.logs_dir:
            args.logs_dir = paper2_root / "logs"

    # Default benchmark scan directories
    benchmark_scan_dirs = list(args.benchmark_scan_dir)
    if not benchmark_scan_dirs:
        benchmark_scan_dirs = [args.results_dir]

    # Default benchmark file globs
    benchmark_file_globs = list(args.benchmark_file_glob) if args.benchmark_file_glob else ["benchmark*.json"]

    # Merge mainline_a_run_aliases: start with defaults, update with CLI-provided
    mainline_a_run_aliases = dict(defaults.mainline_a_run_aliases)
    if args.mainline_a_alias:
        for alias_str in args.mainline_a_alias:
            if "=" in alias_str:
                key, value = alias_str.split("=", 1)
                mainline_a_run_aliases[key.strip()] = value.strip()

    return DashboardConfig(
        logs_dir=args.logs_dir,
        experiments_dir=args.experiments_dir,
        results_dir=args.results_dir,
        figures_dir=args.figures_dir,
        backup_scan_dirs=list(args.backup_scan_dir),
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
        paper2_root=paper2_root,
        paper2_python=args.paper2_python,
        mainline_a_enabled=args.mainline_a_enabled,
        benchmark_scan_dirs=benchmark_scan_dirs,
        benchmark_file_globs=benchmark_file_globs,
        mainline_a_run_aliases=mainline_a_run_aliases,
    )
