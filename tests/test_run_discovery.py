"""Tests for run discovery helpers."""

from dashboard.config import DashboardConfig
from dashboard.run_discovery import (
    discover_legacy_runs,
    discover_runs,
    discover_structured_runs,
    load_benchmark_results,
    select_latest_run,
)


def test_discover_structured_runs():
    runs = discover_structured_runs("tests/fixtures/structured")

    assert any(run.run_id == "run_001" and run.source_type == "legacy_structured" for run in runs)


def test_discover_legacy_runs():
    runs = discover_legacy_runs("tests/fixtures/legacy")

    assert len(runs) == 1
    assert runs[0].run_id == "test"
    assert runs[0].stdout_file.name == "benchmark_full_test.log"
    assert runs[0].stderr_file.name == "benchmark_full_test.err.log"


def test_discover_runs_mixed_merge(tmp_path):
    logs_dir = tmp_path / "logs"
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "test"
    logs_dir.mkdir()
    run_dir.mkdir(parents=True)
    (logs_dir / "benchmark_full_test.log").write_text("Algorithm: GRPO\n", encoding="utf-8")
    (logs_dir / "benchmark_full_test.err.log").write_text("Training GRPOAgent: 1it [00:01, 1.0it/s]\n", encoding="utf-8")
    (run_dir / "run_meta.json").write_text('{"schema_version":1,"run_id":"test"}', encoding="utf-8")
    (run_dir / "events.jsonl").write_text('{"type":"algorithm_started","algorithm":"GRPO"}\n', encoding="utf-8")

    cfg = DashboardConfig(
        logs_dir=logs_dir,
        benchmark_json=tmp_path / "benchmark.json",
        runs_dir=runs_dir,
        host="127.0.0.1",
        port=8088,
        scan_interval_sec=1.0,
        stall_threshold_sec=120,
        recent_log_limit=100,
        sse_interval_sec=1.0,
    )
    runs = discover_runs(cfg)
    test_run = next(run for run in runs if run.run_id == "test")

    assert test_run.source_type == "mixed"
    assert test_run.run_dir == run_dir
    assert test_run.meta_file == run_dir / "run_meta.json"
    assert test_run.stdout_file == logs_dir / "benchmark_full_test.log"
    assert test_run.stderr_file == logs_dir / "benchmark_full_test.err.log"


def test_select_latest_run():
    runs = discover_structured_runs("tests/fixtures/structured") + discover_legacy_runs("tests/fixtures/legacy")

    assert select_latest_run(runs) is not None


def test_load_benchmark_results():
    results = load_benchmark_results("tests/fixtures/legacy/benchmark.json")

    assert len(results) == 1
    assert results[0].algorithm == "GRPO"
    assert results[0].source == "benchmark_json"
    assert results[0].status == "historical"
    assert results[0].latency == 0.12
    assert results[0].update_count == 481436
