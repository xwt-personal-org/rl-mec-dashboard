"""API tests for paper2 experiment endpoints."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

from dashboard.api import create_app
from dashboard.config import DashboardConfig


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_health_reports_experiment_state_support(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "status": "running", "records": []}),
        encoding="utf-8",
    )
    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/health")

    assert payload["status"] == "ok"
    assert payload["version"] == "0.3.0"
    assert payload["has_experiment_state"] is True
    assert payload["default_run_id"] == "paper2_full_17_vscode"
    assert payload["quick_run_id"] == "vscode_quick"


def test_list_runs_contains_full17_and_quick_placeholders(tmp_path):
    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs")

    runs = {run["run_id"]: run for run in payload["runs"]}
    assert "paper2_full_17_vscode" in runs
    assert "vscode_quick" in runs
    for run in runs.values():
        for key in (
            "run_id",
            "display_name",
            "status",
            "current_algorithm",
            "progress_pct",
            "total_algorithms",
            "source_type",
            "has_error",
            "last_error",
            "is_placeholder",
        ):
            assert key in run
    assert runs["paper2_full_17_vscode"]["is_placeholder"] is True
    assert runs["vscode_quick"]["is_placeholder"] is True


def test_get_run_detail_contains_records_and_artifact_paths(tmp_path):
    experiments_dir = tmp_path / "experiments"
    results_dir = tmp_path / "results"
    run_dir = experiments_dir / "paper2_full_17_vscode"
    result_dir = run_dir / "artifacts" / "GRPO"
    result_dir.mkdir(parents=True)
    results_dir.mkdir()
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": "paper2_full_17_vscode", "name": "Full 17", "algorithms": [{"name": "GRPO"}]}),
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
    (result_dir / "result.json").write_text(
        json.dumps(
            {
                "algorithm": "GRPO",
                "seed": 42,
                "device": "cpu",
                "final_eval": {"eval/reward_mean": 1.0},
            }
        ),
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
        payload = _get_json(base_url, "/api/runs/paper2_full_17_vscode")

    record = payload["records"][0]
    assert record["stdout_path"].replace("\\", "/").endswith("artifacts/GRPO/stdout.log")
    assert record["stderr_path"].replace("\\", "/").endswith("artifacts/GRPO/stderr.log")
    assert record["result_path"].replace("\\", "/").endswith("artifacts/GRPO/result.json")
    assert record["result_missing"] is False
    assert payload["results"][0]["algorithm"] == "GRPO"
    assert payload["results"][0]["seed"] == 42
    assert payload["results"][0]["final_eval"]["eval/reward_mean"] == 1.0
    assert payload["benchmark_export_path"].replace("\\", "/").endswith(
        "results/benchmark_paper2_full_17_vscode.json"
    )
    assert "process_marker_exists" in payload
    assert "possibly_stale" in payload


def test_stdout_log_endpoint_returns_tail(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "vscode_quick"
    log_dir = run_dir / "artifacts" / "GRPO"
    log_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": "vscode_quick", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "vscode_quick", "records": [{"name": "GRPO", "status": "running"}]}),
        encoding="utf-8",
    )
    (log_dir / "stdout.log").write_text("hello\n" + "x" * 20, encoding="utf-8")
    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
            log_tail_bytes=10,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/vscode_quick/logs/GRPO/stdout")

    assert payload["run_id"] == "vscode_quick"
    assert payload["algorithm"] == "GRPO"
    assert payload["stream"] == "stdout"
    assert payload["exists"] is True
    assert payload["text"] == "x" * 10


def test_missing_log_endpoint_returns_exists_false(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "vscode_quick"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": "vscode_quick", "algorithms": [{"name": "GRPO"}]}),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "vscode_quick", "records": [{"name": "GRPO", "status": "running"}]}),
        encoding="utf-8",
    )
    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/vscode_quick/logs/GRPO/stderr")

    assert payload["exists"] is False
    assert payload["text"] == ""


def test_unknown_algorithm_log_endpoint_returns_404(tmp_path):
    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get_json(base_url, "/api/runs/vscode_quick/logs/MISSING/stdout")

    assert exc_info.value.code == 404


def test_benchmark_export_empty_array_is_valid(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "benchmark_vscode_quick.json").write_text("[]", encoding="utf-8")
    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=results_dir,
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/vscode_quick/benchmark")

    assert payload == {"run_id": "vscode_quick", "exists": True, "results": []}


def test_missing_benchmark_export_is_not_500(tmp_path):
    with _api_server(
        DashboardConfig(
            experiments_dir=tmp_path / "experiments",
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        payload = _get_json(base_url, "/api/runs/vscode_quick/benchmark")

    assert payload == {"run_id": "vscode_quick", "exists": False, "results": []}


def test_sse_endpoint_exists_for_experiment_run(tmp_path):
    experiments_dir = tmp_path / "experiments"
    run_dir = experiments_dir / "vscode_quick"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": "vscode_quick", "status": "running", "records": []}),
        encoding="utf-8",
    )
    with _api_server(
        DashboardConfig(
            experiments_dir=experiments_dir,
            results_dir=tmp_path / "results",
            logs_dir=tmp_path / "logs",
            scan_interval_sec=60.0,
        )
    ) as base_url:
        response = urllib.request.urlopen(base_url + "/api/runs/vscode_quick/events", timeout=5)
        try:
            assert response.status == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
        finally:
            response.close()


def test_fixture_api_end_to_end():
    with _api_server(
        DashboardConfig(
            experiments_dir=FIXTURES_DIR / "experiments",
            results_dir=FIXTURES_DIR / "results",
            logs_dir=FIXTURES_DIR / "legacy",
            scan_interval_sec=60.0,
            log_tail_bytes=4096,
        )
    ) as base_url:
        health = _get_json(base_url, "/api/health")
        runs_payload = _get_json(base_url, "/api/runs")
        quick = _get_json(base_url, "/api/runs/vscode_quick")
        stderr_payload = _get_json(base_url, "/api/runs/vscode_quick/logs/GRPO/stderr")
        benchmark = _get_json(base_url, "/api/runs/vscode_quick/benchmark")

    assert health["has_experiment_state"] is True
    run_ids = {run["run_id"] for run in runs_payload["runs"]}
    assert {"paper2_full_17_vscode", "vscode_quick"}.issubset(run_ids)
    assert quick["status"] == "failed"
    assert quick["records"][0]["name"] == "GRPO"
    assert stderr_payload["exists"] is True
    assert "Traceback" in stderr_payload["text"]
    assert benchmark == {"run_id": "vscode_quick", "exists": True, "results": []}


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
