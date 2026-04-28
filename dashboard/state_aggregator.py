"""Run state aggregation from structured protocol and legacy logs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from dashboard.config import DashboardConfig
from dashboard.log_parser import parse_log_line
from dashboard.models import AlgorithmResult, RecentLogEntry, RunDescriptor, RunState
from dashboard.protocol_reader import StructuredRunReader
from dashboard.run_discovery import load_benchmark_results


class RunStateAggregator:
    def __init__(self, config: DashboardConfig):
        self.config = config

    def initialize_state(self, descriptor: RunDescriptor) -> RunState:
        return RunState(
            run_id=descriptor.run_id,
            source_type=descriptor.source_type,
            stdout_file=str(descriptor.stdout_file or ""),
            stderr_file=str(descriptor.stderr_file or ""),
            has_structured_protocol=descriptor.source_type in ("structured", "mixed"),
            last_log_time=descriptor.mtime,
            updated_at=descriptor.mtime,
        )

    def apply_structured_events(self, state: RunState, events: list[dict[str, Any]]) -> RunState:
        for event in events:
            self._apply_event(state, event)
        return state

    def read_legacy_events_since(self, path: Path, state: RunState) -> list[dict[str, Any]]:
        path = Path(path)
        if not path.exists():
            state.log_offsets.pop(str(path), None)
            return []

        key = str(path)
        offset = state.log_offsets.get(key, 0)
        if offset < 0 or offset > path.stat().st_size:
            offset = 0

        events: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            for line in f:
                events.extend(parse_log_line(line, source_file=key))
            state.log_offsets[key] = f.tell()
        return events

    def apply_legacy_log_events(self, state: RunState, events: list[dict[str, Any]]) -> RunState:
        for event in events:
            self._apply_event(state, event)
        return state

    def merge_results(self, state: RunState, fallback_results: list[AlgorithmResult]) -> RunState:
        candidates = [_coerce_result(result) for result in state.results]
        candidates.extend(fallback_results)
        candidates = [result for result in candidates if result is not None]

        by_algorithm: dict[str, AlgorithmResult] = {}
        grouped: dict[str, list[AlgorithmResult]] = {}
        for result in candidates:
            grouped.setdefault(result.algorithm, []).append(result)
            current = by_algorithm.get(result.algorithm)
            if current is None or _result_priority(result) > _result_priority(current):
                by_algorithm[result.algorithm] = result

        fill_fields = (
            "latency",
            "energy",
            "deadline_miss_rate",
            "throughput",
            "comm_score",
            "update_count",
            "environment",
        )
        for algorithm, result in by_algorithm.items():
            fallbacks = sorted(grouped.get(algorithm, []), key=_result_priority, reverse=True)
            for field_name in fill_fields:
                value = getattr(result, field_name)
                if value not in (None, ""):
                    continue
                for fallback in fallbacks:
                    fallback_value = getattr(fallback, field_name)
                    if fallback_value not in (None, ""):
                        setattr(result, field_name, fallback_value)
                        break

        state.results = sorted(
            by_algorithm.values(),
            key=lambda result: result.train_time if result.train_time is not None else 0,
        )
        return state

    def compute_overall_progress(self, state: RunState) -> RunState:
        current_frac = 0.0
        if state.current_step > 0 and state.total_step > 0 and state.status not in ("finished", "failed"):
            current_frac = state.current_step / state.total_step
        state.overall_progress = len(state.completed_algorithms) + round(current_frac, 2)
        return state

    def compute_status(self, state: RunState) -> RunState:
        if state.status in ("finished", "failed"):
            return state
        now = time.time()
        if state.completed_algorithms and len(state.completed_algorithms) >= state.total_algorithms:
            state.status = "finished"
        elif state.current_step > 0 and now - state.last_log_time > self.config.stall_threshold_sec:
            state.status = "stalled"
        elif state.current_step > 0 or state.current_algorithm:
            state.status = "running"
        elif state.degraded:
            state.status = "degraded"
        else:
            state.status = "idle"
        return state

    def scan_once(self, descriptor: RunDescriptor, state: RunState) -> RunState:
        try:
            state.source_type = descriptor.source_type
            state.has_structured_protocol = descriptor.source_type in ("structured", "mixed")
            state.stdout_file = str(descriptor.stdout_file or state.stdout_file or "")
            state.stderr_file = str(descriptor.stderr_file or state.stderr_file or "")
            state.last_log_time = max(state.last_log_time, descriptor.mtime)

            if descriptor.run_dir and descriptor.source_type in ("structured", "mixed"):
                reader = StructuredRunReader(descriptor.run_dir)
                meta = reader.read_meta()
                if meta:
                    state.status = meta.status
                    state.total_algorithms = len(meta.algorithms) or state.total_algorithms
                offset_key = str(reader.events_path)
                events, new_offset = reader.read_events_since(state.event_offsets.get(offset_key, 0))
                state.event_offsets[offset_key] = new_offset
                self.apply_structured_events(state, events)
                state.results.extend(reader.read_summary())

            legacy_paths = []
            if descriptor.stdout_file:
                legacy_paths.append(descriptor.stdout_file)
            if descriptor.stderr_file and descriptor.stderr_file not in legacy_paths:
                legacy_paths.append(descriptor.stderr_file)
            for path in legacy_paths:
                events = self.read_legacy_events_since(path, state)
                self.apply_legacy_log_events(state, events)

            fallback_results = load_benchmark_results(self.config.benchmark_json)
            self.merge_results(state, fallback_results)
            self.compute_overall_progress(state)
            self.compute_status(state)
            state.updated_at = time.time()
            return state
        except Exception as exc:
            state.degraded = True
            state.last_error = f"Scan error: {exc}"
            if state.status not in ("finished", "failed"):
                state.status = "degraded"
            state.updated_at = time.time()
            return state

    def _apply_event(self, state: RunState, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        state.updated_at = time.time()
        source_file = str(event.get("source_file", ""))
        if source_file:
            state.last_log_time = time.time()

        if event_type == "algorithm_started":
            state.current_algorithm = str(event.get("algorithm", ""))
            if state.status not in ("finished", "failed"):
                state.status = "running"
            return

        if event_type == "progress":
            state.current_algorithm = str(event.get("algorithm") or state.current_algorithm)
            state.current_step = int(event.get("current_step", state.current_step) or 0)
            total_step = int(event.get("total_step", state.total_step) or 0)
            if total_step > 0:
                state.total_step = total_step
            state.it_per_sec = float(event.get("it_per_sec", state.it_per_sec) or 0.0)
            state.eta_seconds = int(event.get("eta_seconds", state.eta_seconds) or 0)
            if state.total_step > 0:
                state.progress_pct = round(state.current_step / state.total_step * 100, 2)
            if state.status not in ("finished", "failed"):
                state.status = "running"
            return

        if event_type == "elapsed":
            state.elapsed_seconds = float(event.get("elapsed_seconds", state.elapsed_seconds) or 0.0)
            return

        if event_type == "eta":
            state.eta_seconds = int(event.get("eta_seconds", state.eta_seconds) or 0)
            return

        if event_type == "update_count":
            state.update_count = int(event.get("update_count", state.update_count) or 0)
            return

        if event_type == "algorithm_finished":
            result = _result_from_event(event)
            if result:
                state.results.append(result)
                if result.algorithm not in state.completed_algorithms:
                    state.completed_algorithms.append(result.algorithm)
            return

        if event_type == "benchmark_finished" or event_type == "run_finished":
            state.status = "finished"
            return

        if event_type == "run_failed":
            state.status = "failed"
            state.last_error = str(event.get("message", "Run failed"))
            return

        if event_type == "algorithm_count":
            total = int(event.get("total_algorithms", state.total_algorithms) or state.total_algorithms)
            state.total_algorithms = max(state.total_algorithms, total)
            return

        if event_type in ("log", "error"):
            level = "error" if event_type == "error" else str(event.get("level", "info"))
            text = str(event.get("text", event.get("message", "")))
            state.recent_logs.append(
                RecentLogEntry(
                    time=str(event.get("time", "")),
                    level=level,
                    text=text,
                    source_file=source_file,
                )
            )
            if len(state.recent_logs) > self.config.recent_log_limit:
                state.recent_logs = state.recent_logs[-self.config.recent_log_limit :]
            if event_type == "error":
                state.last_error = text
                state.degraded = True


def _result_from_event(event: dict[str, Any]) -> AlgorithmResult | None:
    result = event.get("result")
    if isinstance(result, AlgorithmResult):
        return result
    return _coerce_result(event)


def _coerce_result(result: AlgorithmResult | dict[str, Any] | None) -> AlgorithmResult | None:
    if isinstance(result, AlgorithmResult):
        return result
    if not isinstance(result, dict):
        return None
    algorithm = result.get("algorithm")
    if not algorithm:
        return None
    return AlgorithmResult(
        algorithm=str(algorithm),
        reward=_optional_float(result.get("reward")),
        reward_std=_optional_float(result.get("reward_std")),
        train_time=_optional_float(result.get("train_time")),
        latency=_optional_float(result.get("latency")),
        energy=_optional_float(result.get("energy")),
        deadline_miss_rate=_optional_float(result.get("deadline_miss_rate")),
        throughput=_optional_float(result.get("throughput")),
        comm_score=_optional_float(result.get("comm_score")),
        update_count=_optional_int(result.get("update_count")),
        environment=str(result.get("environment", "")),
        source=result.get("source", "log"),
        status=result.get("status", "finished"),
    )


def _result_priority(result: AlgorithmResult) -> int:
    return {"historical": 0, "benchmark_json": 1, "log": 2, "structured": 3}.get(result.source, 0)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(float(value))
