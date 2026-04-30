"""Benchmark export loader compatibility tests."""

import json
from pathlib import Path

from dashboard.run_discovery import load_benchmark_results


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_new_benchmark_export_fields(tmp_path):
    benchmark = tmp_path / "benchmark_run.json"
    benchmark.write_text(
        json.dumps(
            [
                {
                    "algorithm": "GRPO",
                    "final_reward_mean": 2.0,
                    "final_reward_mean_mean": 1.0,
                    "final_reward_std": 0.2,
                    "final_latency_mean": 10.0,
                    "final_energy_mean": 3.0,
                    "final_comm_score": 0.9,
                    "train_timesteps": 100000,
                    "checkpoint_dir": "checkpoints/GRPO",
                    "seed": 42,
                    "device": "cpu",
                    "status": "finished",
                }
            ]
        ),
        encoding="utf-8",
    )

    results = load_benchmark_results(benchmark)

    assert len(results) == 1
    result = results[0]
    assert result.algorithm == "GRPO"
    assert result.reward == 2.0
    assert result.reward_std == 0.2
    assert result.latency == 10.0
    assert result.energy == 3.0
    assert result.comm_score == 0.9
    assert result.train_timesteps == 100000
    assert result.checkpoint_dir == "checkpoints/GRPO"
    assert result.seed == 42
    assert result.device == "cpu"
    assert result.status == "finished"


def test_empty_benchmark_array_is_valid():
    results = load_benchmark_results(FIXTURES_DIR / "edge_cases" / "benchmark_empty.json")

    assert results == []
