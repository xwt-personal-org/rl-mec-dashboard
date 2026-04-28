"""Tests for dashboard models and configuration parsing."""

from dashboard.config import create_default_config, parse_cli_args
from dashboard.models import AlgorithmResult, RunState, run_state_to_dict


def test_run_state_defaults():
    state = RunState(run_id="run_001")

    assert state.run_id == "run_001"
    assert state.status == "idle"
    assert state.current_step == 0
    assert state.total_step == 500000
    assert state.total_algorithms == 17
    assert state.has_structured_protocol is False
    assert state.source_type == "legacy_log"


def test_algorithm_result_defaults():
    result = AlgorithmResult(algorithm="GRPO")

    assert result.algorithm == "GRPO"
    assert result.reward is None
    assert result.source == "log"
    assert result.status == "finished"


def test_run_state_to_dict_contains_frontend_fields():
    data = run_state_to_dict(RunState(run_id="run_001"))

    for key in (
        "run_id",
        "status",
        "current_algorithm",
        "current_step",
        "total_step",
        "progress_pct",
        "it_per_sec",
        "eta_seconds",
        "elapsed_seconds",
        "update_count",
        "completed_algorithms",
        "results",
        "last_error",
        "updated_at",
        "process_alive",
        "recent_logs",
        "overall_progress",
        "degraded",
        "total_algorithms",
        "stderr_file",
        "stdout_file",
        "has_structured_protocol",
        "source_type",
    ):
        assert key in data


def test_parse_cli_args_runs_dir():
    cfg = parse_cli_args(["--logs-dir", "logs", "--runs-dir", "runs", "--port", "8090"])

    assert str(cfg.logs_dir) == "logs"
    assert str(cfg.runs_dir) == "runs"
    assert cfg.port == 8090


def test_create_default_config_port():
    cfg = create_default_config()

    assert cfg.port == 8088
