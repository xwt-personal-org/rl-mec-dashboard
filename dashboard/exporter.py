"""Result export helpers for dashboard runs."""

from __future__ import annotations

import csv
import io

from dashboard.models import AlgorithmResult, RunState

CSV_COLUMNS = [
    "run_id",
    "algorithm",
    "reward",
    "reward_std",
    "latency",
    "energy",
    "deadline_miss_rate",
    "throughput",
    "comm_score",
    "train_time",
    "update_count",
    "seed",
    "device",
    "train_timesteps",
    "checkpoint_dir",
    "result_path",
    "status",
    "source",
]

MARKDOWN_COLUMNS = [
    "Run",
    "Algorithm",
    "Reward",
    "Latency",
    "Energy",
    "Deadline Miss",
    "Throughput",
    "Comm Score",
    "Train Time",
    "Device",
    "Timesteps",
    "Status",
]


def normalize_result_row(run_id: str, result: AlgorithmResult) -> dict[str, str]:
    return {
        "run_id": run_id,
        "algorithm": _stringify(result.algorithm),
        "reward": _stringify(result.reward),
        "reward_std": _stringify(result.reward_std),
        "latency": _stringify(result.latency),
        "energy": _stringify(result.energy),
        "deadline_miss_rate": _stringify(result.deadline_miss_rate),
        "throughput": _stringify(result.throughput),
        "comm_score": _stringify(result.comm_score),
        "train_time": _stringify(result.train_time),
        "update_count": _stringify(result.update_count),
        "seed": _stringify(result.seed),
        "device": _stringify(result.device),
        "train_timesteps": _stringify(result.train_timesteps),
        "checkpoint_dir": _stringify(result.checkpoint_dir),
        "result_path": _stringify(result.result_path),
        "status": _stringify(result.status),
        "source": _stringify(result.source),
    }


def results_to_csv(states: list[RunState]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for state in states:
        for result in state.results:
            writer.writerow(normalize_result_row(state.run_id, result))
    return output.getvalue()


def results_to_markdown(states: list[RunState]) -> str:
    rows = [
        [
            row["run_id"],
            row["algorithm"],
            row["reward"],
            row["latency"],
            row["energy"],
            row["deadline_miss_rate"],
            row["throughput"],
            row["comm_score"],
            row["train_time"],
            row["device"],
            row["train_timesteps"],
            row["status"],
        ]
        for state in states
        for row in (normalize_result_row(state.run_id, result) for result in state.results)
    ]
    lines = [
        "| " + " | ".join(MARKDOWN_COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(MARKDOWN_COLUMNS)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _stringify(value) -> str:
    if value is None:
        return ""
    return str(value)
