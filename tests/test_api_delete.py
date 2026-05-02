"""API tests for controlled local deletion endpoints."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

from dashboard.api import create_app
from dashboard.config import DashboardConfig


def test_delete_preview_returns_confirm_token(tmp_path):
    experiments_dir = tmp_path / "experiments"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    _write_backup(backup_dir)
    with _api_server(
        DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results", scan_interval_sec=60.0)
    ) as base_url:
        payload = _post_json(
            base_url,
            "/api/delete-preview",
            {"target_id": "backup:paper2_full_17_vscode_backup_20260501_150000"},
        )

    assert payload["blocked"] is False
    assert payload["confirm_token"]
    assert payload["paths"] == [str(backup_dir.resolve())]


def test_delete_confirm_removes_source_files_and_refreshes_runs(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "custom_run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "custom_run", "status": "completed"}),
        encoding="utf-8",
    )
    with _api_server(
        DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results", scan_interval_sec=60.0)
    ) as base_url:
        preview = _post_json(base_url, "/api/delete-preview", {"target_id": "active_run:custom_run"})
        result = _post_json(
            base_url,
            "/api/delete-confirm",
            {"target_id": "active_run:custom_run", "confirm_token": preview["confirm_token"]},
        )
        runs_payload = _get_json(base_url, "/api/runs")
        targets_payload = _get_json(base_url, "/api/delete-targets")

    assert result["deleted_paths"] == [str(run_dir.resolve())]
    assert not run_dir.exists()
    assert "custom_run" not in {run["run_id"] for run in runs_payload["runs"]}
    assert "active_run:custom_run" not in {target["target_id"] for target in targets_payload["targets"]}


def test_delete_confirm_rejects_running_experiment(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "running"}),
        encoding="utf-8",
    )
    with _api_server(
        DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results", scan_interval_sec=60.0)
    ) as base_url:
        preview = _post_json(base_url, "/api/delete-preview", {"target_id": "active_run:paper2_full_17_vscode"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                base_url,
                "/api/delete-confirm",
                {"target_id": "active_run:paper2_full_17_vscode", "confirm_token": preview["confirm_token"]},
            )

    assert preview["blocked"] is True
    assert exc_info.value.code == 409
    assert run_dir.exists()


def test_delete_confirm_rejects_invalid_token(tmp_path):
    experiments_dir = tmp_path / "experiments"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    _write_backup(backup_dir)
    with _api_server(
        DashboardConfig(experiments_dir=experiments_dir, results_dir=tmp_path / "results", scan_interval_sec=60.0)
    ) as base_url:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                base_url,
                "/api/delete-confirm",
                {
                    "target_id": "backup:paper2_full_17_vscode_backup_20260501_150000",
                    "confirm_token": "bad-token",
                },
            )

    assert exc_info.value.code == 409
    assert backup_dir.exists()


def test_delete_confirm_removes_legacy_log_source_files(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    stdout_file = logs_dir / "benchmark_full_legacy.log"
    stderr_file = logs_dir / "benchmark_full_legacy.err.log"
    stdout_file.write_text("legacy stdout", encoding="utf-8")
    stderr_file.write_text("legacy stderr", encoding="utf-8")

    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            logs_dir=logs_dir,
            scan_interval_sec=60.0,
        )
    ) as base_url:
        targets = _get_json(base_url, "/api/delete-targets")
        preview = _post_json(base_url, "/api/delete-preview", {"target_id": "legacy_log:legacy"})
        result = _post_json(
            base_url,
            "/api/delete-confirm",
            {"target_id": "legacy_log:legacy", "confirm_token": preview["confirm_token"]},
        )
        refreshed_targets = _get_json(base_url, "/api/delete-targets")

    assert "legacy_log:legacy" in {target["target_id"] for target in targets["targets"]}
    assert preview["blocked"] is False
    assert set(result["deleted_paths"]) == {str(stdout_file.resolve()), str(stderr_file.resolve())}
    assert not stdout_file.exists()
    assert not stderr_file.exists()
    assert "legacy_log:legacy" not in {target["target_id"] for target in refreshed_targets["targets"]}


@contextmanager
def _api_server(config: DashboardConfig):
    port = _free_port()
    config.port = port
    app = create_app(config)
    server_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", access_log=False)
    server = uvicorn.Server(server_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(base_url)
    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def _wait_for_server(base_url: str) -> None:
    deadline = time.time() + 10
    last_error = None
    while time.time() < deadline:
        try:
            _get_json(base_url, "/api/health")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"API test server did not start: {last_error}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _get_json(base_url: str, path: str):
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(base_url: str, path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


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
