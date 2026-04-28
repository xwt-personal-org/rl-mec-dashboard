"""Structured experiment protocol reader."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from dashboard.models import AlgorithmResult, LogLevel, RunMeta


def read_json_file(path: Path) -> dict[str, Any] | list[Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc


def read_jsonl_since(path: Path, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    path = Path(path)
    if not path.exists():
        return [], 0
    if offset < 0 or offset > path.stat().st_size:
        offset = 0

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        new_offset = f.tell()
    return rows, new_offset


def read_jsonl_tail(path: Path, limit: int = 1000) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows, _ = read_jsonl_since(path, 0)
    return rows[-limit:]


class StructuredRunReader:
    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.meta_path = self.run_dir / "run_meta.json"
        self.events_path = self.run_dir / "events.jsonl"
        self.metrics_path = self.run_dir / "metrics.jsonl"
        self.summary_path = self.run_dir / "summary.json"

    def exists(self) -> bool:
        return self.run_dir.exists() and self.meta_path.exists()

    def read_meta(self) -> RunMeta | None:
        payload = read_json_file(self.meta_path)
        if not isinstance(payload, dict):
            return None
        return RunMeta(
            run_id=str(payload.get("run_id", self.run_dir.name)),
            created_at=str(payload.get("created_at", "")),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            status=payload.get("status", "idle"),
            environment=str(payload.get("environment", "")),
            algorithms=list(payload.get("algorithms", [])),
            seeds=list(payload.get("seeds", [])),
            config_hash=str(payload.get("config_hash", "")),
            config_summary=dict(payload.get("config_summary", {})),
            paper2_git_commit=payload.get("paper2_git_commit"),
        )

    def read_events_since(self, offset: int) -> tuple[list[dict[str, Any]], int]:
        events, new_offset = read_jsonl_since(self.events_path, offset)
        return [event for event in (normalize_structured_event(raw) for raw in events) if event], new_offset

    def read_metrics_tail(self, limit: int = 1000) -> list[dict[str, Any]]:
        return read_jsonl_tail(self.metrics_path, limit)

    def read_summary(self) -> list[AlgorithmResult]:
        payload = read_json_file(self.summary_path)
        if not isinstance(payload, dict):
            return []
        results = payload.get("results", [])
        if not isinstance(results, list):
            return []
        parsed: list[AlgorithmResult] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            result = _algorithm_result_from_payload(item, source="structured")
            if result:
                parsed.append(result)
        return parsed


def normalize_structured_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    event_type = raw.get("type")
    if event_type == "algorithm_started":
        algorithm = raw.get("algorithm")
        if not algorithm:
            return None
        return {
            "type": "algorithm_started",
            "time": raw.get("time", ""),
            "algorithm": str(algorithm),
            "message": raw.get("message", ""),
            "source_file": "events.jsonl",
        }
    if event_type == "progress":
        return {
            "type": "progress",
            "time": raw.get("time", ""),
            "algorithm": raw.get("algorithm", ""),
            "current_step": int(raw.get("current_step", 0) or 0),
            "total_step": int(raw.get("total_step", 0) or 0),
            "it_per_sec": float(raw.get("it_per_sec", 0.0) or 0.0),
            "eta_seconds": int(raw.get("eta_seconds", 0) or 0),
            "source_file": "events.jsonl",
        }
    if event_type == "algorithm_finished":
        result = _algorithm_result_from_payload(raw, source="structured")
        if not result:
            return None
        return {
            "type": "algorithm_finished",
            "time": raw.get("time", ""),
            "algorithm": result.algorithm,
            "result": result,
            "source_file": "events.jsonl",
        }
    if event_type in {"log", "error"}:
        level: LogLevel = "error" if event_type == "error" else raw.get("level", "info")
        text = raw.get("message", raw.get("text", ""))
        return {
            "type": event_type,
            "time": raw.get("time", ""),
            "level": level,
            "text": str(text),
            "source_file": "events.jsonl",
        }
    if event_type in {"benchmark_finished", "run_finished", "run_failed"}:
        return {
            "type": event_type,
            "time": raw.get("time", ""),
            "message": raw.get("message", ""),
            "source_file": "events.jsonl",
        }
    return None


def _algorithm_result_from_payload(payload: dict[str, Any], source: str) -> AlgorithmResult | None:
    algorithm = payload.get("algorithm")
    if not algorithm:
        return None
    return AlgorithmResult(
        algorithm=str(algorithm),
        reward=_optional_float(payload.get("reward")),
        reward_std=_optional_float(payload.get("reward_std")),
        train_time=_optional_float(payload.get("train_time")),
        latency=_optional_float(payload.get("latency")),
        energy=_optional_float(payload.get("energy")),
        deadline_miss_rate=_optional_float(payload.get("deadline_miss_rate")),
        throughput=_optional_float(payload.get("throughput")),
        comm_score=_optional_float(payload.get("comm_score")),
        update_count=_optional_int(payload.get("update_count")),
        environment=str(payload.get("environment", "")),
        source=source,
        status="finished",
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
