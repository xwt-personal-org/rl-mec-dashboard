"""Tests for paper2 experiment run discovery."""

import json

from dashboard.config import DashboardConfig
from dashboard.run_discovery import default_experiment_placeholders, discover_experiment_runs, discover_runs


def test_discover_experiment_runs_finds_state_json(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    run_dir.mkdir(parents=True)
    results_dir.mkdir()
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "name": "Full 17"}),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text('{"status":"running"}', encoding="utf-8")
    (experiments_dir / ".index.sqlite3").write_text("ignored", encoding="utf-8")

    runs = discover_experiment_runs(experiments_dir, results_dir)

    assert len(runs) == 1
    assert runs[0].run_id == "paper2_full_17_vscode"
    assert runs[0].display_name == "Full 17"
    assert runs[0].source_type == "experiment_state"
    assert runs[0].experiment_dir == run_dir
    assert runs[0].run_json_file == run_dir / "run.json"
    assert runs[0].state_json_file == run_dir / "state.json"
    assert runs[0].benchmark_export_file == results_dir / "benchmark_paper2_full_17_vscode.json"


def test_default_placeholders_are_added_when_files_missing(tmp_path):
    cfg = DashboardConfig(experiments_dir=tmp_path / "experiments", results_dir=tmp_path / "results")

    placeholders = default_experiment_placeholders(cfg)

    assert [item.run_id for item in placeholders] == ["paper2_full_17_vscode", "vscode_quick"]
    assert all(item.source_type == "placeholder" for item in placeholders)
    assert all(item.is_placeholder for item in placeholders)
    assert placeholders[0].display_name == "Paper2 Full 17 Algorithms VSCode Benchmark"
    assert placeholders[1].display_name == "VSCode Quick Benchmark"


def test_default_placeholders_skip_existing_experiment(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text('{"status":"running"}', encoding="utf-8")
    cfg = DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results")

    placeholders = default_experiment_placeholders(cfg)

    assert [item.run_id for item in placeholders] == ["vscode_quick"]


def test_experiment_descriptor_wins_over_legacy_same_run_id(tmp_path):
    experiments_dir = tmp_path / "experiments"
    logs_dir = tmp_path / "logs"
    runs_dir = tmp_path / "runs"
    experiment_dir = experiments_dir / "same"
    structured_dir = runs_dir / "same"
    experiment_dir.mkdir(parents=True)
    logs_dir.mkdir()
    structured_dir.mkdir(parents=True)
    (experiment_dir / "state.json").write_text('{"run_id":"same","status":"running"}', encoding="utf-8")
    (structured_dir / "run_meta.json").write_text('{"schema_version":1,"run_id":"same"}', encoding="utf-8")
    (structured_dir / "events.jsonl").write_text("", encoding="utf-8")
    (logs_dir / "benchmark_same.log").write_text("Algorithm: GRPO\n", encoding="utf-8")
    cfg = DashboardConfig(
        experiments_dir=experiments_dir,
        results_dir=tmp_path / "results",
        runs_dir=runs_dir,
        logs_dir=logs_dir,
    )

    runs = discover_runs(cfg)

    same = next(item for item in runs if item.run_id == "same")
    assert same.source_type == "experiment_state"
    assert same.experiment_dir == experiment_dir
    assert same.run_dir is None
    assert same.stdout_file is None
