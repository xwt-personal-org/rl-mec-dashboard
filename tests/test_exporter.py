"""Exporter tests for dashboard run results."""

import csv
import io

from dashboard.exporter import CSV_COLUMNS, results_to_csv, results_to_markdown
from dashboard.models import AlgorithmResult, RunState


def test_results_to_csv_header():
    csv_text = results_to_csv([])

    assert csv_text.splitlines()[0] == ",".join(CSV_COLUMNS)


def test_results_to_csv_contains_algorithm():
    state = RunState(run_id="r1", results=[AlgorithmResult(algorithm="GRPO", reward=1.2)])
    rows = list(csv.DictReader(io.StringIO(results_to_csv([state]))))

    assert rows[0]["run_id"] == "r1"
    assert rows[0]["algorithm"] == "GRPO"


def test_results_to_markdown_contains_header_and_algorithm():
    state = RunState(run_id="r1", results=[AlgorithmResult(algorithm="GRPO", reward=1.2)])
    markdown = results_to_markdown([state])

    assert "| Run | Algorithm | Reward |" in markdown
    assert "GRPO" in markdown


def test_none_values_export_as_empty_string():
    state = RunState(run_id="r1", results=[AlgorithmResult(algorithm="GRPO")])
    rows = list(csv.DictReader(io.StringIO(results_to_csv([state]))))

    assert rows[0]["reward"] == ""
    assert rows[0]["latency"] == ""


def test_export_includes_new_result_fields():
    result = AlgorithmResult(
        algorithm="GRPO",
        seed=42,
        device="cpu",
        train_timesteps=100000,
        checkpoint_dir="checkpoints/GRPO",
        result_path="artifacts/GRPO/result.json",
    )
    state = RunState(run_id="r1", results=[result])
    rows = list(csv.DictReader(io.StringIO(results_to_csv([state]))))
    markdown = results_to_markdown([state])

    assert rows[0]["seed"] == "42"
    assert rows[0]["device"] == "cpu"
    assert rows[0]["train_timesteps"] == "100000"
    assert rows[0]["checkpoint_dir"] == "checkpoints/GRPO"
    assert rows[0]["result_path"] == "artifacts/GRPO/result.json"
    assert "| Run | Algorithm | Reward |" in markdown
    assert "cpu" in markdown
