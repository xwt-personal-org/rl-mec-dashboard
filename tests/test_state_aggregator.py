"""Tests for dashboard run state aggregation."""

import time

from dashboard.config import DashboardConfig
from dashboard.models import AlgorithmResult, RunDescriptor, RunState
from dashboard.state_aggregator import RunStateAggregator


def make_config(tmp_path=None):
    base = tmp_path if tmp_path is not None else None
    return DashboardConfig(
        logs_dir=(base / "logs") if base else "tests/fixtures/legacy",
        benchmark_json=(base / "benchmark.json") if base else "tests/fixtures/legacy/benchmark.json",
        runs_dir=(base / "runs") if base else "tests/fixtures/structured",
        host="127.0.0.1",
        port=8088,
        scan_interval_sec=1.0,
        stall_threshold_sec=120,
        recent_log_limit=3,
        sse_interval_sec=1.0,
    )


def test_initialize_state_sets_descriptor_fields():
    descriptor = RunDescriptor(run_id="run_001", source_type="legacy_structured", mtime=1.0, display_name="run_001")
    state = RunStateAggregator(make_config()).initialize_state(descriptor)

    assert state.run_id == "run_001"
    assert state.source_type == "legacy_structured"
    assert state.has_structured_protocol is True
    assert state.last_log_time == 1.0


def test_apply_structured_events_updates_progress_result_and_logs():
    agg = RunStateAggregator(make_config())
    state = agg.apply_structured_events(
        RunState(run_id="run_001"),
        [
            {"type": "algorithm_started", "algorithm": "GRPO"},
            {"type": "progress", "algorithm": "GRPO", "current_step": 10, "total_step": 100, "it_per_sec": 2.0},
            {"type": "algorithm_finished", "result": AlgorithmResult(algorithm="GRPO", reward=1.0, source="structured")},
            {"type": "log", "level": "warn", "text": "High variance detected", "source_file": "events.jsonl"},
        ],
    )

    assert state.current_algorithm == "GRPO"
    assert state.progress_pct == 10.0
    assert state.completed_algorithms == ["GRPO"]
    assert state.results[0].source == "structured"
    assert state.recent_logs[-1].level == "warn"


def test_apply_structured_error_marks_degraded():
    state = RunStateAggregator(make_config()).apply_structured_events(
        RunState(run_id="run_001"),
        [{"type": "error", "level": "error", "text": "Parser failed", "source_file": "events.jsonl"}],
    )

    assert state.degraded is True
    assert state.last_error == "Parser failed"


def test_read_legacy_events_since_tracks_offsets():
    agg = RunStateAggregator(make_config())
    state = RunState(run_id="test")

    first = agg.read_legacy_events_since("tests/fixtures/legacy/benchmark_full_test.log", state)
    second = agg.read_legacy_events_since("tests/fixtures/legacy/benchmark_full_test.log", state)

    assert any(event["type"] == "algorithm_started" for event in first)
    assert second == []


def test_apply_legacy_log_events_updates_algorithm_count():
    state = RunStateAggregator(make_config()).apply_legacy_log_events(
        RunState(run_id="test"),
        [{"type": "algorithm_count", "total_algorithms": 21}],
    )

    assert state.total_algorithms == 21


def test_merge_results_prefers_structured_and_backfills_fields():
    state = RunState(
        run_id="run_001",
        results=[AlgorithmResult(algorithm="GRPO", reward=1.0, source="structured")],
    )
    fallback = [
        AlgorithmResult(
            algorithm="GRPO",
            reward=0.5,
            latency=0.12,
            energy=0.45,
            update_count=481436,
            source="benchmark_json",
            status="historical",
        )
    ]

    merged = RunStateAggregator(make_config()).merge_results(state, fallback)

    assert merged.results[0].source == "structured"
    assert merged.results[0].reward == 1.0
    assert merged.results[0].latency == 0.12
    assert merged.results[0].update_count == 481436


def test_compute_status_running_stalled_and_degraded():
    agg = RunStateAggregator(make_config())
    running = agg.compute_status(RunState(run_id="x", current_step=1, last_log_time=time.time()))
    stalled = agg.compute_status(RunState(run_id="x", current_step=1, last_log_time=0))
    degraded = agg.compute_status(RunState(run_id="x", degraded=True))

    assert running.status == "running"
    assert stalled.status == "stalled"
    assert degraded.status == "degraded"


def test_scan_once_legacy_applies_events_and_benchmark_backfill():
    descriptor = RunDescriptor(
        run_id="test",
        source_type="legacy_log",
        mtime=time.time(),
        display_name="test",
        stdout_file="tests/fixtures/legacy/benchmark_full_test.log",
        stderr_file="tests/fixtures/legacy/benchmark_full_test.err.log",
    )
    agg = RunStateAggregator(make_config())
    state = agg.scan_once(descriptor, agg.initialize_state(descriptor))

    assert state.status == "finished"
    assert state.current_step == 12000
    assert state.results[0].algorithm == "GRPO"
    assert state.results[0].source == "log"
    assert state.results[0].latency == 0.12


def test_scan_once_structured_reads_protocol():
    descriptor = RunDescriptor(
        run_id="run_001",
        source_type="legacy_structured",
        mtime=time.time(),
        display_name="run_001",
        run_dir="tests/fixtures/structured/run_001",
    )
    agg = RunStateAggregator(make_config())
    state = agg.scan_once(descriptor, agg.initialize_state(descriptor))

    assert state.has_structured_protocol is True
    assert state.current_algorithm == "GRPO"
    assert state.current_step == 12000
    assert state.results[0].source == "structured"
