"""Parse paper2 convergence curves from benchmark JSON payloads."""

from __future__ import annotations

import math
from typing import Any

from dashboard.models import ConvergencePoint, ConvergenceSeries, RunConvergencePayload


PAPER2_CONVERGENCE_METRICS = {
    "reward": "eval/reward_mean",
    "latency": "eval/latency_mean",
    "energy": "eval/energy_mean",
    "comm_score": "eval/comm_score",
}

TRAIN_LOG_CONVERGENCE_METRICS = {
    "reward": ("eval_eval/reward_mean", "eval/reward_mean", "reward_mean"),
    "latency": ("eval_eval/latency_mean", "eval/latency_mean"),
    "energy": (
        "eval_eval/energy_mean",
        "eval_eval/energy_per_task_mean",
        "eval/energy_mean",
        "eval/energy_per_task_mean",
    ),
    "comm_score": ("eval_eval/comm_score", "eval/comm_score"),
}

CONVERGENCE_LABELS = {
    "reward": "Reward",
    "latency": "Latency / Task",
    "energy": "Energy / Task",
    "comm_score": "Comm Score",
}

DEFAULT_EVAL_INTERVAL = 1000
_RECORD_EVAL_INTERVAL_KEY = "_record_eval_interval"


def load_convergence_payload(
    run_id: str,
    source_type: str,
    benchmark_results: list[dict],
    metric: str = "reward",
) -> RunConvergencePayload:
    if metric not in PAPER2_CONVERGENCE_METRICS:
        raise ValueError(f"Unsupported convergence metric: {metric}")

    series = [
        parsed
        for parsed in (parse_algorithm_convergence(record, metric) for record in benchmark_results)
        if parsed is not None and parsed.mean
    ]
    algorithms = [item.algorithm for item in series]
    missing_reason = "" if series else "benchmark export has no convergence_by_seed"
    return RunConvergencePayload(
        run_id=run_id,
        source_type=source_type,
        metrics=[metric],
        algorithms=algorithms,
        series=series,
        missing_reason=missing_reason,
    )


def parse_algorithm_convergence(record: dict, metric: str) -> ConvergenceSeries | None:
    algorithm = str(record.get("algorithm") or "").strip()
    if not algorithm:
        return None

    raw_seed_rows = record.get("convergence_by_seed")
    seed_rows: dict[str, dict] = {}
    if isinstance(raw_seed_rows, dict):
        for seed, row in raw_seed_rows.items():
            if isinstance(row, dict):
                seed_rows[str(seed)] = _with_record_eval_interval(row, record)
    elif isinstance(raw_seed_rows, list):
        for index, row in enumerate(raw_seed_rows):
            if not isinstance(row, dict):
                continue
            seed = row.get("seed", index)
            seed_rows[str(seed)] = _with_record_eval_interval(row, record)
    else:
        return None

    if not seed_rows:
        return None
    series = aggregate_seed_series(algorithm, metric, seed_rows)
    return series if series.mean else None


def load_train_log_convergence_payload(
    run_id: str,
    source_type: str,
    train_log_records: list[dict],
    metric: str = "reward",
) -> RunConvergencePayload:
    if metric not in PAPER2_CONVERGENCE_METRICS:
        raise ValueError(f"Unsupported convergence metric: {metric}")

    grouped: dict[str, dict[str, dict]] = {}
    for index, record in enumerate(train_log_records):
        algorithm = str(record.get("algorithm") or "").strip()
        train_log = record.get("train_log")
        if not algorithm or not isinstance(train_log, dict):
            continue
        values = _train_log_values(train_log, metric)
        if not values:
            continue
        seed = str(record.get("seed") or index)
        eval_interval = _coerce_eval_interval(record.get("eval_interval"))
        if eval_interval == DEFAULT_EVAL_INTERVAL and not record.get("eval_interval"):
            eval_interval = _infer_eval_interval(record.get("train_timesteps"), len(values))
        grouped.setdefault(algorithm, {})[seed] = {
            PAPER2_CONVERGENCE_METRICS[metric]: values,
            "eval_interval": eval_interval,
            "steps": _infer_steps(
                record.get("train_timesteps"),
                len(values),
                eval_interval,
                bool(record.get("eval_interval")),
            ),
        }

    series = [
        parsed
        for parsed in (aggregate_seed_series(algorithm, metric, seed_rows) for algorithm, seed_rows in grouped.items())
        if parsed.mean
    ]
    return RunConvergencePayload(
        run_id=run_id,
        source_type=source_type,
        metrics=[metric],
        algorithms=[item.algorithm for item in series],
        series=series,
        missing_reason="" if series else "train_logs.json has no convergence metric data",
    )


def aggregate_seed_series(
    algorithm: str,
    metric: str,
    seed_rows: dict[str, dict],
) -> ConvergenceSeries:
    metric_key = PAPER2_CONVERGENCE_METRICS[metric]
    seed_series: dict[str, list[ConvergencePoint]] = {}
    eval_interval = DEFAULT_EVAL_INTERVAL

    for seed, row in seed_rows.items():
        if not isinstance(row, dict):
            continue
        row_interval = _coerce_eval_interval(
            row.get("eval_interval", row.get(_RECORD_EVAL_INTERVAL_KEY, DEFAULT_EVAL_INTERVAL))
        )
        values = row.get(metric_key)
        if not isinstance(values, list) or not values:
            continue
        if not seed_series:
            eval_interval = row_interval
        steps = _coerce_steps(row.get("steps"), len(values), row_interval)
        seed_series[str(seed)] = [
            ConvergencePoint(
                step=steps[index],
                value=_optional_finite_float(value),
                seed=str(seed),
            )
            for index, value in enumerate(values)
        ]

    if not seed_series:
        return ConvergenceSeries(
            algorithm=algorithm,
            metric=metric,
            label=CONVERGENCE_LABELS[metric],
            eval_interval=eval_interval,
        )

    min_length = min(len(points) for points in seed_series.values() if points)
    seed_series = {seed: points[:min_length] for seed, points in seed_series.items() if points}

    mean_points: list[ConvergencePoint] = []
    std_points: list[ConvergencePoint] = []
    first_seed_points = next(iter(seed_series.values()))
    for index in range(min_length):
        values = [points[index].value for points in seed_series.values() if points[index].value is not None]
        step = first_seed_points[index].step
        if not values:
            mean_points.append(ConvergencePoint(step=step, value=None))
            std_points.append(ConvergencePoint(step=step, value=None))
            continue
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        mean_points.append(ConvergencePoint(step=step, value=mean_value))
        std_points.append(ConvergencePoint(step=step, value=math.sqrt(variance)))

    converged, reason = detect_convergence([point.value for point in mean_points])
    return ConvergenceSeries(
        algorithm=algorithm,
        metric=metric,
        label=CONVERGENCE_LABELS[metric],
        eval_interval=eval_interval,
        seed_series=seed_series,
        mean=mean_points,
        std=std_points,
        converged=converged,
        convergence_reason=reason,
    )


def detect_convergence(mean_values: list[float | None]) -> tuple[bool, str]:
    values = [value for value in mean_values if value is not None and math.isfinite(value)]
    if len(values) < 3:
        return False, "not enough points"

    window_size = max(2, math.ceil(len(values) * 0.1))
    tail = values[-window_size:]
    denominator = max(abs(tail[0]), 1e-12)
    relative_change = (max(tail) - min(tail)) / denominator
    percent = relative_change * 100.0
    if relative_change < 0.05:
        return True, f"tail relative change {percent:.1f}% < 5%"
    return False, f"tail relative change {percent:.1f}% >= 5%"


def _with_record_eval_interval(row: dict, record: dict) -> dict:
    if "eval_interval" in row:
        return dict(row)
    enriched = dict(row)
    if "eval_interval" in record:
        enriched[_RECORD_EVAL_INTERVAL_KEY] = record.get("eval_interval")
    return enriched


def _coerce_eval_interval(value: Any) -> int:
    if isinstance(value, bool):
        return DEFAULT_EVAL_INTERVAL
    try:
        interval = int(float(value))
    except (TypeError, ValueError):
        return DEFAULT_EVAL_INTERVAL
    return interval if interval > 0 else DEFAULT_EVAL_INTERVAL


def _optional_finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _train_log_values(train_log: dict, metric: str) -> list[Any]:
    for key in TRAIN_LOG_CONVERGENCE_METRICS[metric]:
        values = train_log.get(key)
        if isinstance(values, list) and values:
            return values
    return []


def _infer_eval_interval(train_timesteps: Any, value_count: int) -> int:
    if value_count < 2:
        return DEFAULT_EVAL_INTERVAL
    try:
        timesteps = int(float(train_timesteps))
    except (TypeError, ValueError):
        return DEFAULT_EVAL_INTERVAL
    if timesteps <= 0:
        return DEFAULT_EVAL_INTERVAL
    return max(1, int(round(timesteps / (value_count - 1))))


def _infer_steps(
    train_timesteps: Any,
    value_count: int,
    eval_interval: int,
    has_explicit_interval: bool,
) -> list[int]:
    if value_count <= 0:
        return []
    if has_explicit_interval:
        return [index * eval_interval for index in range(value_count)]
    try:
        timesteps = int(float(train_timesteps))
    except (TypeError, ValueError):
        return [index * eval_interval for index in range(value_count)]
    if timesteps <= 0 or value_count == 1:
        return [index * eval_interval for index in range(value_count)]
    return [int(round(index * timesteps / (value_count - 1))) for index in range(value_count)]


def _coerce_steps(value: Any, value_count: int, eval_interval: int) -> list[int]:
    if isinstance(value, list) and len(value) >= value_count:
        steps: list[int] = []
        for item in value[:value_count]:
            try:
                step = int(round(float(item)))
            except (TypeError, ValueError):
                break
            steps.append(step if step >= 0 else 0)
        if len(steps) == value_count:
            return steps
    return [index * eval_interval for index in range(value_count)]
