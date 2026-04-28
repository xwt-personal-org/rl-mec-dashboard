"""Dashboard domain models and API DTO helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal

RunStatus = Literal["idle", "running", "finished", "stalled", "degraded", "failed"]
ResultSource = Literal["structured", "log", "benchmark_json", "historical"]
ResultStatus = Literal["pending", "running", "finished", "failed", "historical"]
LogLevel = Literal["debug", "info", "warn", "error"]
SourceType = Literal["structured", "legacy_log", "mixed"]


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
    source: ResultSource = "log"
    status: ResultStatus = "finished"


@dataclass
class RecentLogEntry:
    time: str
    level: LogLevel
    text: str
    source_file: str = ""


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


@dataclass
class RunState:
    run_id: str
    status: RunStatus = "idle"
    current_algorithm: str = ""
    current_step: int = 0
    total_step: int = 500000
    progress_pct: float = 0.0
    it_per_sec: float = 0.0
    eta_seconds: int = 0
    elapsed_seconds: float = 0.0
    update_count: int = 0
    completed_algorithms: list[str] = field(default_factory=list)
    results: list[AlgorithmResult | dict[str, Any]] = field(default_factory=list)
    last_error: str = ""
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
