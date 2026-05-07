import json
import math

import pytest

from dashboard.convergence import (
    aggregate_seed_series,
    detect_convergence,
    load_convergence_payload,
    load_train_log_convergence_payload,
    parse_algorithm_convergence,
)
from dashboard.run_discovery import load_benchmark_payload


def test_parse_convergence_by_seed_dict_reward():
    record = _mock_benchmark_results_with_convergence()[0]

    series = parse_algorithm_convergence(record, "reward")

    assert series is not None
    assert series.algorithm == "GRPO"
    assert series.metric == "reward"
    assert series.label == "Reward"
    assert series.eval_interval == 1000
    assert series.seed_series["42"][1].step == 1000
    assert series.mean[0].value == -10.0
    assert series.converged is True


def test_parse_convergence_by_seed_list_format():
    record = {
        "algorithm": "PPO",
        "eval_interval": 500,
        "convergence_by_seed": [
            {"seed": 7, "eval/reward_mean": [1.0, 2.0, 2.1]},
            {"seed": 8, "eval/reward_mean": [1.2, 2.2, 2.3]},
        ],
    }

    series = parse_algorithm_convergence(record, "reward")

    assert series is not None
    assert set(series.seed_series) == {"7", "8"}
    assert series.eval_interval == 500
    assert series.mean[1].step == 500
    assert series.mean[1].value == pytest.approx(2.1)


def test_aggregate_seed_series_aligns_to_shortest_seed():
    series = aggregate_seed_series(
        "SAC",
        "reward",
        {
            "1": {"eval/reward_mean": [1.0, 2.0, 3.0], "eval_interval": 100},
            "2": {"eval/reward_mean": [3.0, 4.0], "eval_interval": 100},
        },
    )

    assert len(series.mean) == 2
    assert len(series.seed_series["1"]) == 2
    assert series.mean[0].value == pytest.approx(2.0)
    assert series.std[0].value == pytest.approx(1.0)


def test_detect_convergence_uses_tail_window():
    converged, reason = detect_convergence([-10.0, -8.0, -6.0, -5.5, -5.3])

    assert converged is True
    assert "tail relative change" in reason
    assert "< 5%" in reason


def test_non_finite_values_are_returned_as_none_and_skipped():
    series = aggregate_seed_series(
        "DDQN",
        "reward",
        {
            "1": {"eval/reward_mean": [1.0, math.nan, 3.0], "eval_interval": 1000},
            "2": {"eval/reward_mean": [2.0, 4.0, math.inf], "eval_interval": 1000},
        },
    )

    assert series.seed_series["1"][1].value is None
    assert series.mean[1].value == 4.0
    assert series.mean[2].value == 3.0


def test_load_convergence_payload_lists_algorithms_with_series():
    payload = load_convergence_payload("r1", "experiment_state", _mock_benchmark_results_with_convergence())

    assert payload.run_id == "r1"
    assert payload.metrics == ["reward"]
    assert payload.algorithms == ["GRPO"]
    assert payload.missing_reason == ""


def test_load_benchmark_payload_preserves_convergence_by_seed(tmp_path):
    path = tmp_path / "benchmark_r1.json"
    path.write_text(json.dumps(_mock_benchmark_results_with_convergence() + ["skip"]), encoding="utf-8")

    payload = load_benchmark_payload(path)

    assert len(payload) == 1
    assert "convergence_by_seed" in payload[0]


def test_load_train_log_convergence_payload_maps_eval_eval_reward():
    payload = load_train_log_convergence_payload(
        "r1",
        "experiment_state",
        [
            {
                "algorithm": "GRPO",
                "seed": 42,
                "train_timesteps": 4000,
                "train_log": {"eval_eval/reward_mean": [-10.0, -8.0, -6.0, -5.0, -4.0]},
            }
        ],
    )

    assert payload.algorithms == ["GRPO"]
    assert payload.series[0].seed_series["42"][1].step == 1000
    assert payload.series[0].mean[-1].step == 4000
    assert payload.series[0].mean[-1].value == -4.0


def test_load_train_log_convergence_payload_keeps_final_timestep_exact():
    payload = load_train_log_convergence_payload(
        "r1",
        "experiment_state",
        [
            {
                "algorithm": "GRPO",
                "seed": 42,
                "train_timesteps": 100000,
                "train_log": {
                    "eval_eval/reward_mean": [-10.0, -8.0, -6.0, -5.0, -4.0, -3.0],
                },
            }
        ],
    )

    assert payload.series[0].mean[1].step == 20000
    assert payload.series[0].mean[-1].step == 100000


def _mock_benchmark_results_with_convergence():
    return [
        {
            "algorithm": "GRPO",
            "convergence_by_seed": {
                "42": {
                    "eval/reward_mean": [-10.0, -8.0, -6.0, -5.5, -5.3],
                    "eval/latency_mean": [0.5, 0.4, 0.35, 0.33, 0.32],
                    "eval/energy_mean": [1.0, 0.9, 0.85, 0.82, 0.81],
                    "eval/comm_score": [10.0, 12.0, 14.0, 14.5, 14.8],
                    "eval_interval": 1000,
                    "total_timesteps": 5000,
                }
            },
        }
    ]
