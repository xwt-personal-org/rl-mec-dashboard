"""Tests for paper2 experiment state aggregation."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dashboard.config import DashboardConfig
from dashboard.models import RunDescriptor
from dashboard.state_aggregator import RunStateAggregator


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_scan_experiment_once_builds_run_state_from_state_json(tmp_path):
    experiment_dir = tmp_path / "experiments" / "paper2_full_17_vscode"
    results_dir = tmp_path / "results"
    experiment_dir.mkdir(parents=True)
    results_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "name": "Full 17",
                "algorithms": [{"name": "GRPO"}, {"name": "PPO"}, {"name": "SAC"}],
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "status": "running",
                "current_index": 1,
                "records": [
                    {"name": "GRPO", "status": "completed"},
                    {"name": "PPO", "status": "running"},
                    {"name": "SAC", "status": "pending"},
                ],
                "completed_algorithms": ["GRPO"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "process.json").write_text('{"pid":123}', encoding="utf-8")
    descriptor = RunDescriptor(
        run_id="paper2_full_17_vscode",
        source_type="experiment_state",
        display_name="Full 17 descriptor",
        experiment_dir=experiment_dir,
        benchmark_export_file=results_dir / "benchmark_paper2_full_17_vscode.json",
    )
    agg = RunStateAggregator(DashboardConfig(results_dir=results_dir, experiments_dir=tmp_path / "experiments"))
    state = agg.scan_experiment_once(descriptor, agg.initialize_state(descriptor))

    assert state.run_id == "paper2_full_17_vscode"
    assert state.display_name == "Full 17"
    assert state.status == "running"
    assert state.current_algorithm == "PPO"
    assert state.current_index == 1
    assert state.total_algorithms == 3
    assert state.completed_algorithms == ["GRPO"]
    assert state.progress_pct == 33.33
    assert state.overall_progress == 1.0
    assert state.process_marker_exists is True
    assert state.possibly_stale is False
    assert state.benchmark_export_path.endswith("benchmark_paper2_full_17_vscode.json")


def test_completed_missing_result_sets_result_missing_warning(tmp_path):
    experiment_dir = tmp_path / "experiments" / "run_x"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "run_x", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "status": "completed",
                "records": [{"name": "GRPO", "status": "completed"}],
                "completed_algorithms": ["GRPO"],
            }
        ),
        encoding="utf-8",
    )
    descriptor = RunDescriptor(run_id="run_x", source_type="experiment_state", experiment_dir=experiment_dir)
    agg = RunStateAggregator(DashboardConfig(experiments_dir=tmp_path / "experiments"))

    state = agg.scan_experiment_once(descriptor, agg.initialize_state(descriptor))

    assert state.status == "completed"
    assert state.records[0].status == "completed"
    assert state.records[0].result_missing is True
    assert state.results == []
    assert any("Result file missing for GRPO" in item.text for item in state.recent_logs)


def test_scan_once_placeholder_builds_initialized_state():
    descriptor = RunDescriptor(
        run_id="paper2_full_17_vscode",
        source_type="placeholder",
        display_name="Paper2 Full 17 Algorithms VSCode Benchmark",
        is_placeholder=True,
    )
    agg = RunStateAggregator(DashboardConfig())

    state = agg.scan_once(descriptor, agg.initialize_state(descriptor))

    assert state.status == "initialized"
    assert state.display_name == "Paper2 Full 17 Algorithms VSCode Benchmark"
    assert state.records == []
    assert state.current_algorithm == ""
    assert state.progress_pct == 0


def test_benchmark_export_supplements_missing_metric_without_overriding_result_json(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    experiment_dir = experiments_dir / "run_x"
    result_dir = experiment_dir / "artifacts" / "GRPO"
    result_dir.mkdir(parents=True)
    results_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "run_x", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "status": "completed",
                "records": [{"name": "GRPO", "status": "completed"}],
                "completed_algorithms": ["GRPO"],
            }
        ),
        encoding="utf-8",
    )
    (result_dir / "result.json").write_text(
        json.dumps({"algorithm": "GRPO", "final_eval": {"eval/reward_mean": 1.0}}),
        encoding="utf-8",
    )
    benchmark_file = results_dir / "benchmark_run_x.json"
    benchmark_file.write_text(
        json.dumps([{"algorithm": "GRPO", "final_reward_mean": 99.0, "final_latency_mean": 12.5}]),
        encoding="utf-8",
    )
    descriptor = RunDescriptor(
        run_id="run_x",
        source_type="experiment_state",
        experiment_dir=experiment_dir,
        benchmark_export_file=benchmark_file,
    )
    agg = RunStateAggregator(DashboardConfig(experiments_dir=experiments_dir, results_dir=results_dir))

    state = agg.scan_experiment_once(descriptor, agg.initialize_state(descriptor))

    assert len(state.results) == 1
    assert state.results[0].source == "structured"
    assert state.results[0].reward == 1.0
    assert state.results[0].latency == 12.5


def test_quick_failed_points_to_grpo_logs():
    experiment_dir = FIXTURES_DIR / "experiments" / "vscode_quick"
    descriptor = RunDescriptor(run_id="vscode_quick", source_type="experiment_state", experiment_dir=experiment_dir)
    agg = RunStateAggregator(DashboardConfig(experiments_dir=FIXTURES_DIR / "experiments"))

    state = agg.scan_experiment_once(descriptor, agg.initialize_state(descriptor))

    assert state.status == "failed"
    assert state.records[0].name == "GRPO"
    assert state.records[0].status == "failed"
    assert state.records[0].error == "Traceback: fixture failure"
    assert state.records[0].stdout_path.replace("\\", "/").endswith("artifacts/GRPO/stdout.log")
    assert state.records[0].stderr_path.replace("\\", "/").endswith("artifacts/GRPO/stderr.log")
    assert [record.status for record in state.records[1:]] == ["pending", "pending"]


def test_missing_completed_result_is_warning_not_failure(tmp_path):
    experiment_dir = tmp_path / "experiments" / "edge_missing_result"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "edge_missing_result", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        (FIXTURES_DIR / "edge_cases" / "state_missing_result.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    descriptor = RunDescriptor(
        run_id="edge_missing_result",
        source_type="experiment_state",
        experiment_dir=experiment_dir,
    )
    agg = RunStateAggregator(DashboardConfig(experiments_dir=tmp_path / "experiments"))

    state = agg.scan_once(descriptor, agg.initialize_state(descriptor))

    assert state.status == "completed"
    assert state.records[0].result_missing is True
    assert any("Result file missing for GRPO" in item.text for item in state.recent_logs)


def test_invalid_state_json_does_not_crash_scan(tmp_path):
    experiment_dir = tmp_path / "experiments" / "broken"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "broken", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        (FIXTURES_DIR / "edge_cases" / "broken_state.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    descriptor = RunDescriptor(run_id="broken", source_type="experiment_state", experiment_dir=experiment_dir)
    agg = RunStateAggregator(DashboardConfig(experiments_dir=tmp_path / "experiments"))

    state = agg.scan_once(descriptor, agg.initialize_state(descriptor))

    assert state.run_id == "broken"
    assert state.status == "initialized"
    assert any("invalid json file:" in item.text for item in state.recent_logs)
