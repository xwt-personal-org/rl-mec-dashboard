"""Tests for controlled local data deletion."""

import json

from dashboard.config import DashboardConfig
from dashboard.delete_service import LocalDataDeleteService
from dashboard.models import DeleteTarget


def test_delete_service_blocks_paths_outside_allowed_roots(tmp_path):
    outside = tmp_path / "outside" / "backup"
    outside.mkdir(parents=True)
    service = LocalDataDeleteService(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            figures_dir=tmp_path / "figures",
        )
    )

    preview = service._preview_target(
        DeleteTarget(target_id="backup:outside", target_type="backup", display_name="outside", paths=[str(outside)])
    )

    assert preview.blocked is True
    assert "outside allowed roots" in preview.blocked_reason
    assert preview.confirm_token == ""


def test_delete_service_blocks_running_experiment(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "running"}),
        encoding="utf-8",
    )
    service = LocalDataDeleteService(DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results"))

    preview = service.preview_delete("active_run:paper2_full_17_vscode")

    assert preview.blocked is True
    assert "running" in preview.blocked_reason
    assert preview.confirm_token == ""


def test_delete_service_deletes_backup_dir_and_matching_archives(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    figures_dir = tmp_path / "figures"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    benchmark_archive = results_dir / "archive" / "20260501_150000"
    figures_archive = figures_dir / "archive" / "20260501_150000"
    _write_backup(backup_dir)
    benchmark_archive.mkdir(parents=True)
    figures_archive.mkdir(parents=True)
    (benchmark_archive / "benchmark_paper2_full_17_vscode.json").write_text("[]", encoding="utf-8")
    (figures_archive / "reward.png").write_text("png", encoding="utf-8")
    service = LocalDataDeleteService(
        DashboardConfig(experiments_dir=experiments_dir, results_dir=results_dir, figures_dir=figures_dir)
    )

    preview = service.preview_delete("backup:paper2_full_17_vscode_backup_20260501_150000")
    result = service.confirm_delete(preview.target_id, preview.confirm_token)

    assert preview.blocked is False
    assert str(backup_dir.resolve()) in preview.paths
    assert str(benchmark_archive.resolve()) in preview.paths
    assert str(figures_archive.resolve()) in preview.paths
    assert len(result.deleted_paths) == 3
    assert not backup_dir.exists()
    assert not benchmark_archive.exists()
    assert not figures_archive.exists()


def test_list_targets_includes_active_run_backup_archive_and_benchmark_export(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    archive_dir = results_dir / "archive" / "20260501_160000"
    export_file = results_dir / "benchmark_paper2_full_17_vscode.json"
    run_dir.mkdir(parents=True)
    results_dir.mkdir()
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "completed"}),
        encoding="utf-8",
    )
    _write_backup(backup_dir)
    archive_dir.mkdir(parents=True)
    (archive_dir / "benchmark_paper2_full_17_vscode.json").write_text("[]", encoding="utf-8")
    export_file.write_text("[]", encoding="utf-8")
    service = LocalDataDeleteService(DashboardConfig(experiments_dir=experiments_dir, results_dir=results_dir))

    targets = {target.target_id: target for target in service.list_targets()}

    assert "active_run:paper2_full_17_vscode" in targets
    assert "backup:paper2_full_17_vscode_backup_20260501_150000" in targets
    assert "archive:paper2_full_17_vscode_archive_20260501_160000" in targets
    assert "benchmark_export:paper2_full_17_vscode" in targets
    assert targets["active_run:paper2_full_17_vscode"].target_type == "active_run"
    assert targets["benchmark_export:paper2_full_17_vscode"].paths == [str(export_file.resolve())]


def test_list_targets_includes_legacy_logs_structured_runs_and_benchmark_json(tmp_path):
    logs_dir = tmp_path / "logs"
    runs_dir = tmp_path / "runs"
    results_dir = tmp_path / "results"
    logs_dir.mkdir()
    structured_dir = runs_dir / "structured_run"
    structured_dir.mkdir(parents=True)
    results_dir.mkdir()
    stdout_file = logs_dir / "benchmark_full_legacy.log"
    stderr_file = logs_dir / "benchmark_full_legacy.err.log"
    benchmark_json = results_dir / "benchmark.json"
    stdout_file.write_text("legacy stdout", encoding="utf-8")
    stderr_file.write_text("legacy stderr", encoding="utf-8")
    (structured_dir / "run_meta.json").write_text(json.dumps({"run_id": "structured_run"}), encoding="utf-8")
    benchmark_json.write_text("[]", encoding="utf-8")
    service = LocalDataDeleteService(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=results_dir,
            logs_dir=logs_dir,
            runs_dir=runs_dir,
            benchmark_json=benchmark_json,
        )
    )

    targets = {target.target_id: target for target in service.list_targets()}

    assert targets["legacy_log:legacy"].target_type == "legacy_log"
    assert targets["legacy_log:legacy"].paths == [str(stdout_file.resolve()), str(stderr_file.resolve())]
    assert targets["structured_run:structured_run"].target_type == "structured_run"
    assert targets["structured_run:structured_run"].paths == [str(structured_dir.resolve())]
    assert targets["benchmark_json:latest"].target_type == "benchmark_json"
    assert targets["benchmark_json:latest"].paths == [str(benchmark_json.resolve())]
    assert service.preview_delete("legacy_log:legacy").blocked is False


def _write_backup(backup_dir, source_run_id="paper2_full_17_vscode"):
    backup_dir.mkdir(parents=True)
    (backup_dir / "run.json").write_text(
        json.dumps({"run_id": source_run_id, "name": source_run_id, "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (backup_dir / "state.json").write_text(
        json.dumps({"run_id": source_run_id, "status": "completed", "records": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
