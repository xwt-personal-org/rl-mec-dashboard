"""Configuration tests for paper2 experiment paths."""

from dashboard.config import benchmark_export_path, create_default_config, parse_cli_args


def test_default_config_uses_experiments_dir():
    cfg = create_default_config()

    assert cfg.experiments_dir.name == "experiments"
    assert cfg.results_dir.name == "results"
    assert cfg.benchmark_json.as_posix() == "results/benchmark.json"
    assert cfg.default_run_id == "paper2_full_17_vscode"
    assert cfg.quick_run_id == "vscode_quick"
    assert cfg.log_tail_bytes == 65536
    assert cfg.json_retry_keep_last is True


def test_parse_cli_experiments_and_results_dir():
    cfg = parse_cli_args(
        [
            "--experiments-dir",
            "C:/paper2/experiments",
            "--results-dir",
            "C:/paper2/results",
            "--default-run-id",
            "full",
            "--quick-run-id",
            "quick",
            "--log-tail-bytes",
            "1024",
        ]
    )

    assert str(cfg.experiments_dir).endswith("experiments")
    assert str(cfg.results_dir).endswith("results")
    assert cfg.default_run_id == "full"
    assert cfg.quick_run_id == "quick"
    assert cfg.log_tail_bytes == 1024


def test_legacy_runs_dir_does_not_override_experiments_dir():
    cfg = parse_cli_args(["--runs-dir", "legacy_runs"])

    assert str(cfg.runs_dir) == "legacy_runs"
    assert cfg.experiments_dir.name == "experiments"


def test_benchmark_export_path():
    cfg = create_default_config()

    assert benchmark_export_path(cfg, "paper2_full_17_vscode").as_posix().endswith(
        "results/benchmark_paper2_full_17_vscode.json"
    )
