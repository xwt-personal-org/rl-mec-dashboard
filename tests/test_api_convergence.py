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


def test_run_convergence_returns_reward_series(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    _write_run_fixture(experiments_dir / "paper2_full_17_vscode")
    results_dir.mkdir()
    (results_dir / "benchmark_paper2_full_17_vscode.json").write_text(
        json.dumps(_benchmark_payload()),
        encoding="utf-8",
    )

    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/paper2_full_17_vscode/convergence?metric=reward")

    assert payload["run_id"] == "paper2_full_17_vscode"
    assert payload["source_type"] == "experiment_state"
    assert payload["metrics"] == ["reward"]
    assert payload["algorithms"] == ["GRPO"]
    assert payload["series"][0]["algorithm"] == "GRPO"
    assert payload["series"][0]["metric"] == "reward"
    assert payload["series"][0]["mean"][0]["step"] == 0
    assert payload["series"][0]["mean"][0]["value"] == -10.0


def test_run_convergence_returns_empty_payload_without_convergence_data(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    _write_run_fixture(experiments_dir / "paper2_full_17_vscode")
    results_dir.mkdir()
    (results_dir / "benchmark_paper2_full_17_vscode.json").write_text(
        json.dumps([{"algorithm": "GRPO", "final_reward_mean": 1.0}]),
        encoding="utf-8",
    )

    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/paper2_full_17_vscode/convergence")

    assert payload["series"] == []
    assert payload["algorithms"] == []
    assert payload["missing_reason"] == (
        "benchmark export has no convergence_by_seed and train_logs.json has no convergence metric data"
    )


def test_run_convergence_falls_back_to_experiment_train_logs(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    _write_run_fixture(run_dir)
    _write_train_log_fixture(run_dir, "GRPO", [-5.0, -4.5, -4.0])
    results_dir.mkdir()
    (results_dir / "benchmark_paper2_full_17_vscode.json").write_text(
        json.dumps([{"algorithm": "GRPO", "final_reward_mean": -4.0}]),
        encoding="utf-8",
    )

    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/paper2_full_17_vscode/convergence")

    assert payload["missing_reason"] == ""
    assert payload["algorithms"] == ["GRPO"]
    assert payload["series"][0]["mean"][0]["value"] == -5.0
    assert payload["series"][0]["mean"][-1]["step"] == 100000


def test_backup_convergence_reads_archive_benchmark_json(tmp_path):
    results_dir = tmp_path / "results"
    archive_dir = results_dir / "archive" / "20260501_150000"
    archive_dir.mkdir(parents=True)
    (archive_dir / "benchmark_paper2_full_17_vscode.json").write_text(
        json.dumps(_benchmark_payload()),
        encoding="utf-8",
    )

    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(
            base_url,
            "/api/backups/paper2_full_17_vscode_archive_20260501_150000/convergence?metric=reward",
        )

    assert payload["run_id"] == "paper2_full_17_vscode_archive_20260501_150000"
    assert payload["source_type"] == "archive"
    assert payload["series"][0]["mean"][1]["step"] == 1000
    assert payload["series"][0]["mean"][1]["value"] == -8.0


def test_backup_convergence_falls_back_to_backup_train_logs(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    backup_dir = experiments_dir / "paper2_full_17_vscode_backup_20260501_150000"
    _write_run_fixture(backup_dir)
    _write_train_log_fixture(backup_dir, "GRPO", [-6.0, -5.0, -4.0])
    archive_dir = results_dir / "archive" / "20260501_150000"
    archive_dir.mkdir(parents=True)
    (archive_dir / "benchmark_paper2_full_17_vscode.json").write_text(
        json.dumps([{"algorithm": "GRPO", "final_reward_mean": -4.0}]),
        encoding="utf-8",
    )

    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(
            base_url,
            "/api/backups/paper2_full_17_vscode_backup_20260501_150000/convergence?metric=reward",
        )

    assert payload["source_type"] == "backup"
    assert payload["algorithms"] == ["GRPO"]
    assert payload["series"][0]["mean"][0]["value"] == -6.0
    assert payload["series"][0]["mean"][-1]["step"] == 100000


def test_convergence_rejects_unknown_metric(tmp_path):
    _write_run_fixture(tmp_path / "experiments" / "paper2_full_17_vscode")
    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get_json(base_url, "/api/runs/paper2_full_17_vscode/convergence?metric=unknown")

    assert exc_info.value.code == 400


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


def _write_run_fixture(run_dir):
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "name": "Full 17",
                "algorithms": [{"name": "GRPO", "seed": 42, "timesteps": 100000}],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps(
            {
                "run_id": "paper2_full_17_vscode",
                "status": "completed",
                "records": [{"name": "GRPO", "status": "completed"}],
                "completed_algorithms": ["GRPO"],
            }
        ),
        encoding="utf-8",
    )


def _write_train_log_fixture(run_dir, algorithm, rewards):
    train_log_dir = run_dir / "artifacts" / algorithm / "checkpoints"
    train_log_dir.mkdir(parents=True)
    (train_log_dir / "train_logs.json").write_text(
        json.dumps({"eval_eval/reward_mean": rewards}),
        encoding="utf-8",
    )


def _benchmark_payload():
    return [
        {
            "algorithm": "GRPO",
            "convergence_by_seed": {
                "42": {
                    "eval/reward_mean": [-10.0, -8.0, -6.0],
                    "eval/latency_mean": [0.5, 0.4, 0.35],
                    "eval/energy_mean": [1.0, 0.9, 0.85],
                    "eval/comm_score": [10.0, 12.0, 14.0],
                    "eval_interval": 1000,
                }
            },
        }
    ]
