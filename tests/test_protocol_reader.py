"""Tests for structured experiment protocol reading."""

import pytest

from dashboard.models import AlgorithmResult
from dashboard.protocol_reader import (
    StructuredRunReader,
    normalize_structured_event,
    read_json_file,
    read_jsonl_since,
    read_jsonl_tail,
)


def test_read_json_file():
    payload = read_json_file("tests/fixtures/structured/run_001/run_meta.json")

    assert payload["run_id"] == "run_001"
    assert payload["config_summary"]["total_steps"] == 500000


def test_read_jsonl_since():
    events, offset = read_jsonl_since("tests/fixtures/structured/run_001/events.jsonl")

    assert len(events) >= 4
    assert events[0]["type"] == "algorithm_started"
    assert offset > 0


def test_read_jsonl_tail():
    metrics = read_jsonl_tail("tests/fixtures/structured/run_001/metrics.jsonl", limit=1)

    assert len(metrics) == 1
    assert metrics[0]["step"] == 2000


def test_structured_run_reader_exists():
    reader = StructuredRunReader("tests/fixtures/structured/run_001")

    assert reader.exists()


def test_structured_run_reader_read_meta():
    reader = StructuredRunReader("tests/fixtures/structured/run_001")
    meta = reader.read_meta()

    assert meta is not None
    assert meta.run_id == "run_001"
    assert meta.environment == "MEC-v1"
    assert meta.algorithms == ["GRPO", "PPO"]


def test_structured_run_reader_read_summary():
    reader = StructuredRunReader("tests/fixtures/structured/run_001")
    results = reader.read_summary()

    assert len(results) == 1
    assert isinstance(results[0], AlgorithmResult)
    assert results[0].algorithm == "GRPO"
    assert results[0].source == "structured"


def test_normalize_structured_event():
    started = normalize_structured_event({"type": "algorithm_started", "algorithm": "GRPO"})
    finished = normalize_structured_event({"type": "algorithm_finished", "algorithm": "GRPO", "reward": 1.0})
    log = normalize_structured_event({"type": "log", "level": "warn", "message": "High variance detected"})

    assert started["type"] == "algorithm_started"
    assert finished["result"].algorithm == "GRPO"
    assert log["level"] == "warn"
    assert log["text"] == "High variance detected"
    assert log["source_file"] == "events.jsonl"


def test_read_json_file_invalid_json_raises_value_error(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError):
        read_json_file(broken)
