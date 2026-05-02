"""Run discovery and benchmark result loading helpers."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard.config import DashboardConfig
from dashboard.experiment_reader import safe_read_json_file
from dashboard.models import AlgorithmResult, BackupSnapshot, RunDescriptor
from dashboard.protocol_reader import read_json_file


BACKUP_DIR_PATTERN = re.compile(
    r"^(?P<source_run_id>[A-Za-z0-9_.-]+)_(?P<backup_type>backup|auto)_(?P<timestamp>\d{8}_\d{6})$"
)
FLEXIBLE_BACKUP_TOKEN_PATTERN = re.compile(r"_(backup|auto)(?:_|$)", re.IGNORECASE)
TIMESTAMP_PATTERNS = (
    re.compile(r"(?P<date>\d{8})[_-](?P<time>\d{6})"),
    re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})[_-](?P<time>\d{2}-\d{2}-\d{2})"),
)


def parse_backup_dir_name(name: str) -> tuple[str, str, str] | None:
    match = BACKUP_DIR_PATTERN.match(name)
    if match is None:
        return None
    return match.group("source_run_id"), match.group("backup_type"), match.group("timestamp")


def infer_backup_metadata_from_dir(path: Path) -> tuple[str, str, str] | None:
    path = Path(path)
    strict = parse_backup_dir_name(path.name)
    if strict is not None:
        return strict

    name = path.name
    lowered = name.lower()
    backup_type = ""
    source_run_id = ""
    tail = ""
    token_match = FLEXIBLE_BACKUP_TOKEN_PATTERN.search(lowered)
    if token_match:
        backup_type = token_match.group(1).lower()
        source_run_id = name[: token_match.start()].strip("_-. ")
        tail = name[token_match.end() :].strip("_-. ")
    elif lowered.endswith("_backup") or lowered.endswith("-backup") or lowered.endswith(" backup"):
        backup_type = "backup"
        source_run_id = re.sub(r"([_\- ]backup)$", "", name, flags=re.IGNORECASE).strip("_-. ")
    elif lowered.endswith("_auto") or lowered.endswith("-auto") or lowered.endswith(" auto"):
        backup_type = "auto"
        source_run_id = re.sub(r"([_\- ]auto)$", "", name, flags=re.IGNORECASE).strip("_-. ")
    elif "backup" in lowered:
        backup_type = "backup"
    elif "auto" in lowered:
        backup_type = "auto"

    if backup_type not in {"backup", "auto"}:
        return None

    run_payload, _ = safe_read_json_file(path / "run.json")
    if not source_run_id and isinstance(run_payload, dict):
        source_run_id = str(run_payload.get("run_id") or "").strip()
    if not source_run_id:
        return None

    timestamp = _normalize_timestamp(tail or name)
    if not timestamp:
        timestamp = _mtime_timestamp(path)
    return source_run_id, backup_type, timestamp


def is_backup_experiment_dir(path: Path) -> bool:
    return infer_backup_metadata_from_dir(Path(path)) is not None


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
    roots = [] if experiments_dir is None else [Path(experiments_dir)]
    return discover_experiment_backups_from_roots(roots, results_dir)


def discover_experiment_backups_from_roots(roots: list[Path], results_dir: Path) -> list[BackupSnapshot]:
    backups: list[BackupSnapshot] = []
    archive_root = Path(results_dir) / "archive"
    by_id: dict[str, BackupSnapshot] = {}
    for root in roots:
        root = Path(root)
        if not root.exists() or not root.is_dir():
            continue
        for backup_dir in sorted(root.iterdir()):
            if not backup_dir.is_dir():
                continue
            parsed = infer_backup_metadata_from_dir(backup_dir)
            if parsed is None:
                continue
            source_run_id, backup_type, timestamp = parsed
            backup = _backup_snapshot_from_dir(backup_dir, source_run_id, backup_type, timestamp, archive_root)
            existing = by_id.get(backup.backup_id)
            if existing is None or _prefer_backup_snapshot(backup, existing):
                by_id[backup.backup_id] = backup
    return sorted(by_id.values(), key=_backup_sort_key)


def discover_archive_only_backups(results_dir: Path) -> list[BackupSnapshot]:
    archive_root = Path(results_dir) / "archive"
    if not archive_root.exists() or not archive_root.is_dir():
        return []

    backups: list[BackupSnapshot] = []
    for archive_dir in sorted(archive_root.iterdir()):
        if not archive_dir.is_dir():
            continue
        benchmark_files = sorted(item.name for item in archive_dir.glob("benchmark*.json") if item.is_file())
        if not benchmark_files:
            continue
        timestamp = _normalize_timestamp(archive_dir.name) or _mtime_timestamp(archive_dir)
        source_run_id = _source_run_id_from_benchmark_files(benchmark_files)
        backup_id = f"{source_run_id or 'unknown'}_archive_{timestamp}"
        backups.append(
            BackupSnapshot(
                run_id=backup_id,
                backup_id=backup_id,
                backup_type="archive",
                timestamp=timestamp,
                experiment_dir="",
                display_name=source_run_id or f"Archive {timestamp}",
                source_run_id=source_run_id,
                benchmark_archive_dir=str(archive_dir),
                benchmark_files=benchmark_files,
            )
        )
    return sorted(backups, key=_backup_sort_key)


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


def _backup_snapshot_from_dir(
    backup_dir: Path,
    source_run_id: str,
    backup_type: str,
    timestamp: str,
    archive_root: Path,
) -> BackupSnapshot:
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

    return BackupSnapshot(
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


def _prefer_backup_snapshot(candidate: BackupSnapshot, existing: BackupSnapshot) -> bool:
    candidate_has_state = bool(candidate.status or candidate.completed_algorithms or candidate.total_algorithms)
    existing_has_state = bool(existing.status or existing.completed_algorithms or existing.total_algorithms)
    if candidate_has_state != existing_has_state:
        return candidate_has_state
    return bool(candidate.experiment_dir) and not bool(existing.experiment_dir)


def _backup_sort_key(backup: BackupSnapshot) -> tuple[int, str]:
    return -int(re.sub(r"\D", "", backup.timestamp) or "0"), backup.backup_id


def _normalize_timestamp(value: str) -> str:
    text = str(value or "")
    for pattern in TIMESTAMP_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        date = match.group("date").replace("-", "")
        time_part = match.group("time").replace("-", "")
        return f"{date}_{time_part}"
    return ""


def _mtime_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(Path(path).stat().st_mtime).strftime("%Y%m%d_%H%M%S")


def _source_run_id_from_benchmark_files(files: list[str]) -> str:
    for name in files:
        if name == "benchmark.json":
            continue
        match = re.match(r"benchmark_(?P<run_id>.+)\.json$", name)
        if match is not None:
            return match.group("run_id")
    return ""


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
