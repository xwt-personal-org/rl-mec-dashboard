"""Tests for paper2 experiment run discovery."""

import json

from dashboard.config import DashboardConfig
from dashboard.run_discovery import (
    default_experiment_placeholders,
    discover_experiment_backups,
    discover_experiment_runs,
    discover_runs,
    enrich_backup_figures,
)


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


def test_backup_experiment_dirs_are_excluded_from_active_runs(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    active_dir = experiments_dir / "paper2_full_17_vscode"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    auto_dir = experiments_dir / "paper2_full_17_vscode_auto_20260501_160000"
    for path in (active_dir, backup_dir, auto_dir):
        path.mkdir(parents=True)
        (path / "run.json").write_text(
            json.dumps({"run_id": "paper2_full_17_vscode", "name": path.name}),
            encoding="utf-8",
        )
        (path / "state.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")

    runs = discover_experiment_runs(experiments_dir, results_dir)

    assert [run.run_id for run in runs] == ["paper2_full_17_vscode"]
    assert runs[0].experiment_dir == active_dir


def test_active_run_wins_when_backup_has_same_embedded_run_id(tmp_path):
    experiments_dir = tmp_path / "experiments"
    active_dir = experiments_dir / "paper2_full_17_vscode"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    active_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)
    (active_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "running"}),
        encoding="utf-8",
    )
    (backup_dir / "run.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "name": "Backup Copy"}),
        encoding="utf-8",
    )
    (backup_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "completed"}),
        encoding="utf-8",
    )
    cfg = DashboardConfig(
        experiments_dir=experiments_dir,
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
    )

    runs = discover_runs(cfg)

    active = next(run for run in runs if run.run_id == "paper2_full_17_vscode")
    assert active.source_type == "experiment_state"
    assert active.experiment_dir == active_dir
    assert all("backup" not in str(run.experiment_dir) for run in runs if run.experiment_dir is not None)


def test_discover_experiment_backups_reads_backup_metadata(tmp_path):
    experiments_dir = tmp_path / "experiments"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    backup_dir.mkdir(parents=True)
    (backup_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "name": "Full 17",
                "created_at": "2026-05-01T15:00:00",
                "algorithms": [{"name": "GRPO"}, {"name": "PPO"}],
            }
        ),
        encoding="utf-8",
    )
    (backup_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "status": "completed",
                "records": [{"name": "GRPO"}, {"name": "PPO"}, {"name": "SAC"}],
                "completed_algorithms": ["GRPO", "PPO"],
                "updated_at": "2026-05-01T15:01:00",
            }
        ),
        encoding="utf-8",
    )

    backups = discover_experiment_backups(experiments_dir, tmp_path / "results")

    assert len(backups) == 1
    backup = backups[0]
    assert backup.run_id == "paper2_full_17_vscode_backup_20260501_150000"
    assert backup.backup_id == backup.run_id
    assert backup.backup_type == "backup"
    assert backup.timestamp == "20260501_150000"
    assert backup.source_run_id == "paper2_full_17_vscode"
    assert backup.display_name == "Full 17"
    assert backup.status == "completed"
    assert backup.completed_algorithms == 2
    assert backup.total_algorithms == 3
    assert backup.created_at == "2026-05-01T15:00:00"
    assert backup.updated_at == "2026-05-01T15:01:00"
    assert backup.experiment_dir == str(backup_dir)


def test_discover_experiment_backups_links_result_archive_by_timestamp(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    first = experiments_dir / "paper2_full_17_vscode_auto_20260501_150000"
    second = experiments_dir / "paper2_full_17_vscode_backup_20260501_160000"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    for path in (first, second):
        (path / "state.json").write_text("{}", encoding="utf-8")
    archive_dir = results_dir / "archive" / "20260501_150000"
    archive_dir.mkdir(parents=True)
    (archive_dir / "benchmark_paper2_full_17_vscode.json").write_text("[]", encoding="utf-8")
    (archive_dir / "benchmark.json").write_text("[]", encoding="utf-8")
    (archive_dir / "notes.json").write_text("{}", encoding="utf-8")

    backups = discover_experiment_backups(experiments_dir, results_dir)

    assert [backup.timestamp for backup in backups] == ["20260501_160000", "20260501_150000"]
    archived = backups[1]
    assert archived.backup_type == "auto"
    assert archived.benchmark_archive_dir == str(archive_dir)
    assert archived.benchmark_files == ["benchmark.json", "benchmark_paper2_full_17_vscode.json"]


def test_enrich_backup_figures_reads_top_level_files_only(tmp_path):
    experiments_dir = tmp_path / "experiments"
    figures_dir = tmp_path / "figures"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    backup_dir.mkdir(parents=True)
    (backup_dir / "state.json").write_text("{}", encoding="utf-8")
    archive_dir = figures_dir / "archive" / "20260501_150000"
    nested_dir = archive_dir / "archive"
    nested_dir.mkdir(parents=True)
    (archive_dir / "reward.png").write_text("png", encoding="utf-8")
    (archive_dir / "latency.svg").write_text("svg", encoding="utf-8")
    (nested_dir / "old.png").write_text("old", encoding="utf-8")
    backups = discover_experiment_backups(experiments_dir, tmp_path / "results")

    enriched = enrich_backup_figures(backups, figures_dir)

    assert enriched[0].figures_archive_dir == str(archive_dir)
    assert enriched[0].figure_files == ["latency.svg", "reward.png"]
