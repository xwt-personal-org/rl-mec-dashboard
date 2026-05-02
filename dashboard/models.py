"""Dashboard domain models and API DTO helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal

ExperimentStatus = Literal["initialized", "running", "stop_requested", "stopped", "completed", "failed"]
AlgorithmStatus = Literal["pending", "running", "completed", "interrupted", "failed", "skipped"]
SourceType = Literal["experiment_state", "legacy_structured", "legacy_log", "mixed", "placeholder", "backup", "archive"]
RunStatus = Literal[
    "idle",
    "running",
    "finished",
    "stalled",
    "degraded",
    "failed",
    "initialized",
    "stop_requested",
    "stopped",
    "completed",
]
ResultSource = Literal["structured", "log", "benchmark_json", "historical"]
ResultStatus = Literal["pending", "running", "finished", "failed", "historical"]
LogLevel = Literal["debug", "info", "warn", "error"]


@dataclass
class AlgorithmResult:
    algorithm: str
    reward: float | None = None
    reward_std: float | None = None
    train_time: float | None = None
    latency: float | None = None
    energy: float | None = None
    deadline_miss_rate: float | None = None
    throughput: float | None = None
    comm_score: float | None = None
    update_count: int | None = None
    environment: str = ""
    seed: int | None = None
    device: str = ""
    train_timesteps: int | None = None
    checkpoint_dir: str = ""
    result_path: str = ""
    final_eval: dict[str, Any] = field(default_factory=dict)
    source: ResultSource = "log"
    status: ResultStatus = "finished"


@dataclass
class AlgorithmRunRecord:
    name: str
    status: str = "pending"
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    device: str = ""
    result_path: str = ""
    checkpoint_dir: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    error: str | None = None
    result_missing: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"failed", "interrupted"}:
            self.error = None


@dataclass
class RecentLogEntry:
    time: str
    level: LogLevel
    text: str
    source_file: str = ""


@dataclass
class AlgorithmSpec:
    name: str
    config_path: str = ""
    timesteps: int | None = None
    seed: int | None = None
    device: str = ""
    env: str = ""
    eval_episodes: int | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass
class ExperimentRunManifest:
    schema_version: int
    run_id: str
    name: str
    created_at: str
    updated_at: str
    algorithms: list[AlgorithmSpec]
    project_root: str
    output_dir: str
    experiment_dir: str
    metadata: dict[str, Any]


@dataclass
class ExperimentStateSnapshot:
    schema_version: int
    run_id: str
    status: str
    current_index: int
    records: list[AlgorithmRunRecord]
    completed_algorithms: list[str]
    stop_requested: bool
    last_error: str | None
    updated_at: str


@dataclass
class BackupSnapshot:
    run_id: str
    backup_id: str
    backup_type: str
    timestamp: str
    experiment_dir: str
    display_name: str = ""
    source_run_id: str = ""
    status: str = ""
    completed_algorithms: int = 0
    total_algorithms: int = 0
    created_at: str = ""
    updated_at: str = ""
    benchmark_archive_dir: str = ""
    benchmark_files: list[str] = field(default_factory=list)
    figures_archive_dir: str = ""
    figure_files: list[str] = field(default_factory=list)


@dataclass
class DeleteTarget:
    target_id: str
    target_type: str
    display_name: str
    source_run_id: str = ""
    paths: list[str] = field(default_factory=list)
    exists: bool = True
    deletable: bool = True
    blocked_reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class DeletePreview:
    target_id: str
    target_type: str
    display_name: str
    paths: list[str]
    total_files: int
    total_dirs: int
    total_bytes: int
    blocked: bool
    blocked_reason: str = ""
    confirm_token: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class DeleteResult:
    target_id: str
    deleted_paths: list[str]
    skipped_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RunMeta:
    run_id: str
    created_at: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    status: RunStatus = "idle"
    environment: str = ""
    algorithms: list[str] = field(default_factory=list)
    seeds: list[int] = field(default_factory=list)
    config_hash: str = ""
    config_summary: dict[str, Any] = field(default_factory=dict)
    paper2_git_commit: str | None = None


@dataclass
class RunDescriptor:
    run_id: str
    source_type: SourceType = "legacy_log"
    mtime: float = 0.0
    display_name: str = ""
    experiment_dir: Path | None = None
    run_json_file: Path | None = None
    state_json_file: Path | None = None
    process_json_file: Path | None = None
    benchmark_export_file: Path | None = None
    is_placeholder: bool = False
    run_dir: Path | None = None
    stdout_file: Path | None = None
    stderr_file: Path | None = None
    summary_file: Path | None = None
    meta_file: Path | None = None


@dataclass
class RunSummary:
    run_id: str
    display_name: str = ""
    status: RunStatus = "idle"
    current_algorithm: str = ""
    progress_pct: float = 0.0
    overall_progress: float = 0.0
    total_algorithms: int = 17
    updated_at: float = 0.0
    source_type: SourceType = "legacy_log"
    has_error: bool = False
    last_error: str = ""
    is_placeholder: bool = False


@dataclass
class RunState:
    run_id: str
    status: RunStatus = "idle"
    display_name: str = ""
    current_algorithm: str = ""
    current_step: int = 0
    total_step: int = 500000
    progress_pct: float = 0.0
    it_per_sec: float = 0.0
    eta_seconds: int = 0
    elapsed_seconds: float = 0.0
    update_count: int = 0
    records: list[AlgorithmRunRecord | dict[str, Any]] = field(default_factory=list)
    current_index: int = 0
    completed_algorithms: list[str] = field(default_factory=list)
    results: list[AlgorithmResult | dict[str, Any]] = field(default_factory=list)
    last_error: str = ""
    stop_requested: bool = False
    updated_at: float = field(default_factory=time.time)
    process_alive: bool = False
    recent_logs: list[RecentLogEntry | dict[str, Any]] = field(default_factory=list)
    overall_progress: float = 0.0
    degraded: bool = False
    total_algorithms: int = 17
    stderr_file: str = ""
    stdout_file: str = ""
    has_structured_protocol: bool = False
    source_type: SourceType = "legacy_log"
    run_manifest_path: str = ""
    state_path: str = ""
    process_path: str = ""
    benchmark_export_path: str = ""
    process_marker_exists: bool = False
    possibly_stale: bool = False
    schema_version: int = 1
    log_offsets: dict[str, int] = field(default_factory=dict)
    event_offsets: dict[str, int] = field(default_factory=dict)
    last_log_time: float = field(default_factory=time.time)


def dataclass_to_dict(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {item.name: dataclass_to_dict(getattr(obj, item.name)) for item in fields(obj)}
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): dataclass_to_dict(value) for key, value in obj.items()}
    return obj


def algorithm_result_to_dict(result: AlgorithmResult) -> dict[str, Any]:
    return dataclass_to_dict(result)


def run_summary_to_dict(summary: RunSummary) -> dict[str, Any]:
    data = dataclass_to_dict(summary)
    if not data["display_name"]:
        data["display_name"] = data["run_id"]
    return data


def run_state_to_dict(state: RunState) -> dict[str, Any]:
    return dataclass_to_dict(state)
