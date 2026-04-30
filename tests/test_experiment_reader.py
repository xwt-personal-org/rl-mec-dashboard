"""Tests for paper2 experiment file reading."""

import json
from pathlib import Path

from dashboard.experiment_reader import Paper2ExperimentReader, read_text_tail, safe_read_json_file


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_safe_read_json_file_handles_missing_empty_invalid(tmp_path):
    missing_payload, missing_error = safe_read_json_file(tmp_path / "missing.json")
    empty = tmp_path / "empty.json"
    invalid = tmp_path / "invalid.json"
    valid = tmp_path / "valid.json"
    empty.write_text("", encoding="utf-8")
    invalid.write_text("{not valid", encoding="utf-8")
    valid.write_text('{"run_id":"x"}', encoding="utf-8")

    empty_payload, empty_error = safe_read_json_file(empty)
    invalid_payload, invalid_error = safe_read_json_file(invalid)
    valid_payload, valid_error = safe_read_json_file(valid)

    assert missing_payload is None
    assert missing_error is None
    assert empty_payload is None
    assert empty_error.startswith("empty json file:")
    assert invalid_payload is None
    assert invalid_error.startswith("invalid json file:")
    assert valid_payload == {"run_id": "x"}
    assert valid_error is None


def test_read_text_tail_limits_large_log(tmp_path):
    log_file = tmp_path / "stdout.log"
    log_file.write_text("a" * 100 + "tail", encoding="utf-8")

    text, exists = read_text_tail(log_file, max_bytes=8)
    missing_text, missing_exists = read_text_tail(tmp_path / "missing.log", max_bytes=8)

    assert exists is True
    assert text == "aaaatail"
    assert missing_text == ""
    assert missing_exists is False


def test_reader_paths(tmp_path):
    reader = Paper2ExperimentReader(tmp_path / "run_x")

    assert reader.exists() is False
    assert reader.run_json_path == tmp_path / "run_x" / "run.json"
    assert reader.state_json_path == tmp_path / "run_x" / "state.json"
    assert reader.process_json_path == tmp_path / "run_x" / "process.json"
    assert reader.stdout_path("GRPO") == tmp_path / "run_x" / "artifacts" / "GRPO" / "stdout.log"
    assert reader.stderr_path("GRPO") == tmp_path / "run_x" / "artifacts" / "GRPO" / "stderr.log"
    assert reader.default_result_path("GRPO") == tmp_path / "run_x" / "artifacts" / "GRPO" / "result.json"

    reader.state_json_path.parent.mkdir(parents=True)
    reader.state_json_path.write_text("{}", encoding="utf-8")

    assert reader.exists() is True


def test_read_run_manifest_preserves_algorithm_order(tmp_path):
    experiment_dir = tmp_path / "paper2_full_17_vscode"
    experiment_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "paper2_full_17_vscode",
                "name": "Full 17",
                "algorithms": [
                    {"name": "GRPO", "seed": 42, "timesteps": 100},
                    {"name": "PPO"},
                    {"algorithm": "SAC"},
                    {"seed": 7},
                ],
            }
        ),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)

    manifest, error = reader.read_run_manifest()

    assert error is None
    assert manifest.run_id == "paper2_full_17_vscode"
    assert manifest.name == "Full 17"
    assert [spec.name for spec in manifest.algorithms] == ["GRPO", "PPO", "SAC"]
    assert manifest.algorithms[0].seed == 42
    assert manifest.algorithms[0].timesteps == 100


def test_read_state_snapshot_generates_paths(tmp_path):
    experiment_dir = tmp_path / "vscode_quick"
    experiment_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "vscode_quick", "algorithms": [{"name": "GRPO"}, {"name": "PPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "vscode_quick",
                "status": "running",
                "current_index": 1,
                "records": [
                    {"name": "GRPO", "status": "completed", "result_path": "custom/result.json"},
                    {"name": "PPO", "status": "running"},
                ],
                "completed_algorithms": ["GRPO"],
            }
        ),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)
    manifest, _ = reader.read_run_manifest()

    snapshot, error = reader.read_state_snapshot(manifest)

    assert error is None
    assert snapshot.status == "running"
    assert snapshot.current_index == 1
    assert [record.name for record in snapshot.records] == ["GRPO", "PPO"]
    assert snapshot.records[0].result_path == "custom/result.json"
    assert snapshot.records[1].result_path.replace("\\", "/").endswith("artifacts/PPO/result.json")
    assert snapshot.records[1].stdout_path.replace("\\", "/").endswith("artifacts/PPO/stdout.log")
    assert snapshot.completed_algorithms == ["GRPO"]


def test_running_record_ignores_stale_error(tmp_path):
    experiment_dir = tmp_path / "run_x"
    experiment_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "run_x", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "status": "running",
                "records": [
                    {"name": "GRPO", "status": "running", "error": "previous failed attempt", "exit_code": 1}
                ],
            }
        ),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)
    manifest, _ = reader.read_run_manifest()

    snapshot, error = reader.read_state_snapshot(manifest)

    assert error is None
    assert snapshot.records[0].status == "running"
    assert snapshot.records[0].error is None


def test_running_record_ignores_stale_error_fixture(tmp_path):
    experiment_dir = tmp_path / "edge_running"
    experiment_dir.mkdir()
    (experiment_dir / "run.json").write_text(
        json.dumps({"run_id": "edge_running", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (experiment_dir / "state.json").write_text(
        (FIXTURES_DIR / "edge_cases" / "state_running_with_stale_error.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)
    manifest, _ = reader.read_run_manifest()

    snapshot, error = reader.read_state_snapshot(manifest)

    assert error is None
    assert snapshot.records[0].status == "running"
    assert snapshot.records[0].attempts == 2
    assert snapshot.records[0].error is None


def test_read_algorithm_result_maps_final_eval(tmp_path):
    experiment_dir = tmp_path / "paper2_full_17_vscode"
    result_dir = experiment_dir / "artifacts" / "GRPO"
    result_dir.mkdir(parents=True)
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "algorithm": "GRPO",
                "environment": "MEC-v1",
                "seed": 42,
                "device": "cpu",
                "train_timesteps": 100000,
                "checkpoint_dir": "experiments/paper2_full_17_vscode/artifacts/GRPO/checkpoints",
                "final_eval": {
                    "eval/reward_mean": 1.23,
                    "eval/reward_std": 0.1,
                    "eval/latency_mean": 12.5,
                    "eval/energy_mean": 3.4,
                    "eval/comm_score": 0.9,
                },
                "status": "success",
            }
        ),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)
    record = reader._record_from_payload({"name": "GRPO", "status": "completed"})

    result, error = reader.read_algorithm_result(record)

    assert error is None
    assert result.algorithm == "GRPO"
    assert result.reward == 1.23
    assert result.reward_std == 0.1
    assert result.latency == 12.5
    assert result.energy == 3.4
    assert result.comm_score == 0.9
    assert result.seed == 42
    assert result.device == "cpu"
    assert result.train_timesteps == 100000
    assert result.final_eval["eval/reward_mean"] == 1.23


def test_completed_record_missing_result_is_reported(tmp_path):
    experiment_dir = tmp_path / "paper2_full_17_vscode"
    experiment_dir.mkdir()
    reader = Paper2ExperimentReader(experiment_dir)
    record = reader._record_from_payload({"name": "GRPO", "status": "completed"})

    result, error = reader.read_algorithm_result(record)

    assert result is None
    assert error.startswith("result file missing:")


def test_read_algorithm_result_maps_final_eval_fixture():
    reader = Paper2ExperimentReader(FIXTURES_DIR / "experiments" / "paper2_full_17_vscode")
    record = reader._record_from_payload({"name": "GRPO", "status": "completed"})

    result, error = reader.read_algorithm_result(record)

    assert error is None
    assert result.reward == 1.23
    assert result.reward_std == 0.1
    assert result.latency == 12.5
    assert result.energy == 3.4
    assert result.comm_score == 0.9
    assert result.seed == 42
    assert result.final_eval["eval/reward_mean"] == 1.23


def test_read_algorithm_result_resolves_experiments_relative_path(tmp_path):
    experiment_dir = tmp_path / "experiments" / "run_x"
    result_dir = experiment_dir / "artifacts" / "GRPO"
    result_dir.mkdir(parents=True)
    (result_dir / "result.json").write_text(
        json.dumps({"algorithm": "GRPO", "final_eval": {"eval/reward_mean": 7.0}}),
        encoding="utf-8",
    )
    reader = Paper2ExperimentReader(experiment_dir)
    record = reader._record_from_payload(
        {
            "name": "GRPO",
            "status": "completed",
            "result_path": "experiments\\run_x\\artifacts\\GRPO\\result.json",
        }
    )

    result, error = reader.read_algorithm_result(record)

    assert error is None
    assert result.reward == 7.0
