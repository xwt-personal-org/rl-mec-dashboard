"""API tests for the dashboard server."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

from dashboard.api import create_app
from dashboard.config import DashboardConfig


def make_config(port: int):
    return DashboardConfig(
        logs_dir="tests/fixtures/legacy",
        benchmark_json="tests/fixtures/legacy/benchmark.json",
        runs_dir="tests/fixtures/structured",
        host="127.0.0.1",
        port=port,
        scan_interval_sec=60.0,
        stall_threshold_sec=120,
        recent_log_limit=100,
        sse_interval_sec=1.0,
    )


@pytest.fixture(scope="module")
def api_base_url():
    port = _free_port()
    app = create_app(make_config(port))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    deadline = time.time() + 10
    last_error = None
    while time.time() < deadline:
        try:
            _get_json(base_url, "/api/health")
            break
        except Exception as exc:
            last_error = exc
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail(f"API test server did not start: {last_error}")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


def test_health_endpoint(api_base_url):
    status, payload = _get_json(api_base_url, "/api/health")

    assert status == 200
    assert payload["status"] == "ok"
    assert payload["version"] == "0.2.0"
    assert payload["has_structured_protocol"] is True
    assert payload["run_count"] >= 2


def test_runs_endpoint(api_base_url):
    status, payload = _get_json(api_base_url, "/api/runs")

    assert status == 200
    run_ids = {run["run_id"] for run in payload["runs"]}
    assert "run_001" in run_ids
    assert "test" in run_ids


def test_get_run_endpoint(api_base_url):
    status, payload = _get_json(api_base_url, "/api/runs/test")

    assert status == 200
    assert payload["run_id"] == "test"
    assert payload["results"][0]["algorithm"] == "GRPO"


def test_missing_run_returns_404(api_base_url):
    try:
        _get_json(api_base_url, "/api/runs/missing")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("Expected 404 for missing run")


def test_compare_endpoint_reward(api_base_url):
    status, payload = _get_json(api_base_url, "/api/compare?run_ids=test,run_001&metric=reward")

    assert status == 200
    assert payload["metric"] == "reward"
    assert payload["run_ids"] == ["test", "run_001"]
    assert "GRPO" in payload["algorithms"]
    assert payload["series"][0]["values"]


def test_compare_endpoint_invalid_metric(api_base_url):
    try:
        _get_json(api_base_url, "/api/compare?metric=unknown")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("Expected 400 for invalid metric")


def test_export_csv_endpoint(api_base_url):
    status, content, content_type = _get_text(api_base_url, "/api/export/results.csv?run_ids=test")

    assert status == 200
    assert "text/csv" in content_type
    assert "run_id,algorithm,reward" in content
    assert "GRPO" in content


def test_export_markdown_endpoint(api_base_url):
    status, content, content_type = _get_text(api_base_url, "/api/export/results.md?run_ids=test")

    assert status == 200
    assert "text/markdown" in content_type
    assert "| Run | Algorithm | Reward |" in content
    assert "GRPO" in content


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _get_json(base_url: str, path: str):
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _get_text(base_url: str, path: str):
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return response.status, response.read().decode("utf-8"), response.headers.get("content-type", "")
