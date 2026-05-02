"""Run discovery and benchmark result loading helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard.config import DashboardConfig
from dashboard.experiment_reader import safe_read_json_file
from dashboard.models import AlgorithmResult, BackupSnapshot, RunDescriptor
from dashboard.protocol_reader import read_json_file


BACKUP_DIR_PATTERN = re.compile(
    r"^(?P<source_run_id>[A-Za-z0-9_.-]+)_(?P<backup_type>backup|auto)_(?P<timestamp>\d{8}_\d{6})$"
)


def parse_backup_dir_name(name: str) -> tuple[str, str, str] | None:
    match = BACKUP_DIR_PATTERN.match(name)
    if match is None:
        return None
    return match.group("source_run_id"), match.group("backup_type"), match.group("timestamp")


def is_backup_experiment_dir(path: Path) -> bool:
    return parse_backup_dir_name(Path(path).name) is not None


def discover_experiment_runs(experiments_dir: Path | None, results_dir: Path) -> list[RunDescriptor]:
    if experiments_dir is None:
        return []
    experiments_dir = Path(experiments_dir)
    if not experiments_dir.exists():
        return []

    descriptors: list[RunDescriptor] = []
    for experiment_dir in sorted(experiments_dir.iterdir()):
        if not experiment_dir.is_dir():
            continue
        if is_backup_experiment_dir(experiment_dir):
            continue
        run_json_file = experiment_dir / "run.json"
        state_json_file = experiment_dir / "state.json"
        process_json_file = experiment_dir / "process.json"
        experiment_files = [path for path in (run_json_file, state_json_file, process_json_file) if path.exists()]
        if not (run_json_file.exists() or state_json_file.exists()):
            continue

        run_id = experiment_dir.name
        display_name = run_id
        payload, _ = safe_read_json_file(run_json_file)
        if isinstance(payload, dict):
            run_id = str(payload.get("run_id") or run_id)
            display_name = str(payload.get("name") or run_id)

        descriptors.append(
            RunDescriptor(
                run_id=run_id,
                source_type="experiment_state",
                mtime=max(path.stat().st_mtime for path in experiment_files),
                display_name=display_name,
                experiment_dir=experiment_dir,
                run_json_file=run_json_file if run_json_file.exists() else None,
                state_json_file=state_json_file if state_json_file.exists() else None,
                process_json_file=process_json_file if process_json_file.exists() else None,
                benchmark_export_file=Path(results_dir) / f"benchmark_{run_id}.json",
            )
        )
    return descriptors


def discover_experiment_backups(experiments_dir: Path | None, results_dir: Path) -> list[BackupSnapshot]:
    if experiments_dir is None:
        return []
    experiments_dir = Path(experiments_dir)
    if not experiments_dir.exists():
        return []

    backups: list[BackupSnapshot] = []
    archive_root = Path(results_dir) / "archive"
    for backup_dir in sorted(experiments_dir.iterdir()):
        if not backup_dir.is_dir():
            continue
        parsed = parse_backup_dir_name(backup_dir.name)
        if parsed is None:
            continue
        source_run_id, backup_type, timestamp = parsed
        backup_id = f"{source_run_id}_{backup_type}_{timestamp}"

        run_payload, _ = safe_read_json_file(backup_dir / "run.json")
        state_payload, _ = safe_read_json_file(backup_dir / "state.json")
        run_data = run_payload if isinstance(run_payload, dict) else {}
        state_data = state_payload if isinstance(state_payload, dict) else {}

        records = state_data.get("records")
        algorithms = run_data.get("algorithms")
        completed = state_data.get("completed_algorithms")
        total_algorithms = _list_len(records)
        if total_algorithms == 0:
            total_algorithms = _list_len(algorithms)

        benchmark_archive = archive_root / timestamp
        benchmark_archive_dir = ""
        benchmark_files: list[str] = []
        if benchmark_archive.exists() and benchmark_archive.is_dir():
            benchmark_archive_dir = str(benchmark_archive)
            benchmark_files = sorted(item.name for item in benchmark_archive.glob("benchmark*.json") if item.is_file())

        backups.append(
            BackupSnapshot(
                run_id=backup_id,
                backup_id=backup_id,
                backup_type=backup_type,
                timestamp=timestamp,
                experiment_dir=str(backup_dir),
                display_name=str(run_data.get("name") or source_run_id),
                source_run_id=source_run_id,
                status=str(state_data.get("status") or ""),
                completed_algorithms=_list_len(completed),
                total_algorithms=total_algorithms,
                created_at=str(run_data.get("created_at") or state_data.get("created_at") or ""),
                updated_at=str(state_data.get("updated_at") or run_data.get("updated_at") or ""),
                benchmark_archive_dir=benchmark_archive_dir,
                benchmark_files=benchmark_files,
            )
        )
    return sorted(backups, key=lambda item: (-int(item.timestamp.replace("_", "")), item.backup_id))


def enrich_backup_figures(backups: list[BackupSnapshot], figures_dir: Path | None) -> list[BackupSnapshot]:
    if figures_dir is None:
        return backups
    figures_dir = Path(figures_dir)
    if not figures_dir.exists():
        return backups

    for backup in backups:
        candidate = figures_dir / "archive" / backup.timestamp
        if candidate.exists() and candidate.is_dir():
            backup.figures_archive_dir = str(candidate)
            backup.figure_files = sorted(item.name for item in candidate.iterdir() if item.is_file())
    return backups


def default_experiment_placeholders(config: DashboardConfig) -> list[RunDescriptor]:
    existing_run_ids = {
        descriptor.run_id for descriptor in discover_experiment_runs(config.experiments_dir, config.results_dir)
    }
    placeholders = [
        (config.default_run_id, "Paper2 Full 17 Algorithms VSCode Benchmark"),
        (config.quick_run_id, "VSCode Quick Benchmark"),
    ]
    descriptors: list[RunDescriptor] = []
    for run_id, display_name in placeholders:
        if run_id in existing_run_ids:
            continue
        experiment_dir = Path(config.experiments_dir) / run_id if config.experiments_dir is not None else None
        descriptors.append(
            RunDescriptor(
                run_id=run_id,
                source_type="placeholder",
                mtime=0.0,
                display_name=display_name,
                experiment_dir=experiment_dir,
                benchmark_export_file=Path(config.results_dir) / f"benchmark_{run_id}.json",
                is_placeholder=True,
            )
        )
    return descriptors


def discover_structured_runs(runs_dir: Path | None) -> list[RunDescriptor]:
    if runs_dir is None:
        return []
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        return []

    descriptors: list[RunDescriptor] = []
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        meta_file = run_dir / "run_meta.json"
        events_file = run_dir / "events.jsonl"
        summary_file = run_dir / "summary.json"
        structured_files = [path for path in (meta_file, events_file, summary_file) if path.exists()]
        if not structured_files:
            continue

        run_id = run_dir.name
        if meta_file.exists():
            try:
                meta = read_json_file(meta_file)
                if isinstance(meta, dict) and meta.get("run_id"):
                    run_id = str(meta["run_id"])
            except ValueError:
                run_id = run_dir.name

        descriptors.append(
            RunDescriptor(
                run_id=run_id,
                source_type="legacy_structured",
                mtime=max(path.stat().st_mtime for path in structured_files),
                display_name=run_id,
                run_dir=run_dir,
                summary_file=summary_file if summary_file.exists() else None,
                meta_file=meta_file if meta_file.exists() else None,
            )
        )
    return descriptors


def discover_legacy_runs(logs_dir: Path) -> list[RunDescriptor]:
    logs_dir = Path(logs_dir)
    if not logs_dir.exists():
        return []

    descriptors: list[RunDescriptor] = []
    for stdout_file in sorted(logs_dir.glob("benchmark*.log")):
        if stdout_file.name.endswith(".err.log"):
            continue
        stderr_file = stdout_file.parent / f"{stdout_file.stem}.err.log"
        stderr_for_descriptor = stderr_file if stderr_file.exists() else stdout_file
        run_id = stdout_file.stem.replace("benchmark_", "").replace("full_", "")
        mtime = max(stdout_file.stat().st_mtime, stderr_for_descriptor.stat().st_mtime)
        descriptors.append(
            RunDescriptor(
                run_id=run_id,
                source_type="legacy_log",
                mtime=mtime,
                display_name=run_id,
                stdout_file=stdout_file,
                stderr_file=stderr_for_descriptor,
            )
        )
    return descriptors


def discover_runs(config: DashboardConfig) -> list[RunDescriptor]:
    merged: dict[str, RunDescriptor] = {}
    for descriptor in discover_experiment_runs(config.experiments_dir, config.results_dir):
        merged[descriptor.run_id] = descriptor

    for descriptor in discover_structured_runs(config.runs_dir):
        if descriptor.run_id not in merged:
            merged[descriptor.run_id] = descriptor

    for descriptor in discover_legacy_runs(config.logs_dir):
        existing = merged.get(descriptor.run_id)
        if existing is None:
            merged[descriptor.run_id] = descriptor
            continue
        if existing.source_type == "experiment_state":
            continue
        existing.source_type = "mixed"
        existing.mtime = max(existing.mtime, descriptor.mtime)
        existing.stdout_file = descriptor.stdout_file
        existing.stderr_file = descriptor.stderr_file

    for descriptor in default_experiment_placeholders(config):
        if descriptor.run_id not in merged:
            merged[descriptor.run_id] = descriptor

    return sorted(merged.values(), key=lambda item: item.mtime, reverse=True)


def select_latest_run(runs: list[RunDescriptor]) -> RunDescriptor | None:
    if not runs:
        return None
    return max(runs, key=lambda item: item.mtime)


def load_benchmark_results(json_path: Path) -> list[AlgorithmResult]:
    payload = read_json_file(Path(json_path))
    if not isinstance(payload, list):
        return []

    results: list[AlgorithmResult] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        algorithm = item.get("algorithm")
        if not algorithm:
            continue
        results.append(
            AlgorithmResult(
                algorithm=str(algorithm),
                reward=_optional_float(_first_value(item.get("final_reward_mean"), item.get("final_reward_mean_mean"))),
                reward_std=_optional_float(_first_value(item.get("final_reward_std"), item.get("final_reward_mean_std"))),
                train_time=_optional_float(item.get("train_time_seconds_mean")),
                latency=_optional_float(_first_value(item.get("final_latency_mean"), item.get("final_latency_mean_mean"))),
                energy=_optional_float(_first_value(item.get("final_energy_mean"), item.get("final_energy_mean_mean"))),
                deadline_miss_rate=_optional_float(item.get("final_deadline_miss_rate_mean")),
                throughput=_optional_float(item.get("final_throughput_tasks_per_step_mean")),
                comm_score=_optional_float(_first_value(item.get("final_comm_score"), item.get("final_comm_score_mean"))),
                update_count=_optional_int(item.get("total_updates_mean")),
                environment=str(item.get("environment", "")),
                seed=_optional_int(item.get("seed")),
                device=str(item.get("device", "")),
                train_timesteps=_optional_int(item.get("train_timesteps")),
                checkpoint_dir=str(item.get("checkpoint_dir", "")),
                result_path=str(item.get("result_path", "")),
                source="benchmark_json",
                status=str(item.get("status") or "historical"),
            )
        )
    return results


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(float(value))
