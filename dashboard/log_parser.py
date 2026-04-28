"""Legacy benchmark log parsing helpers."""

from __future__ import annotations

import re
from typing import Any

from dashboard.models import AlgorithmResult, algorithm_result_to_dict


def strip_log_prefix(line: str) -> str:
    m = re.search(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+\s+-\s+\w+\s+-\s+(.*)$", line)
    return m.group(1) if m else line


def parse_step_from_tqdm(line: str) -> tuple[int, int, float] | None:
    content = strip_log_prefix(line)
    m = re.search(
        r"Training\s+(\w+Agent):\s+\d+%\|[^|]*\|\s+(\d+)/(\d+)\s+\[[^]]*,\s+([\d.]+)it/s",
        content,
    )
    if m:
        return int(m.group(2)), int(m.group(3)), float(m.group(4))

    m2 = re.search(r"Training\s+\w+Agent:\s+\d+%.*?(\d+)/(\d+).*?([\d.]+)\s*it/s", content)
    if m2:
        return int(m2.group(1)), int(m2.group(2)), float(m2.group(3))

    m3 = re.search(r"Training\s+\w+Agent:\s+(\d+)it\s+\[([^]]+),\s+([\d.]+)it/s", content)
    if m3:
        return int(m3.group(1)), 0, float(m3.group(3))

    return None


def parse_elapsed_from_tqdm(line: str) -> float:
    content = strip_log_prefix(line)
    m = re.search(r"\[(\d+):(\d+):(\d+)<", content)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m2 = re.search(r"\[(\d+):(\d+)<", content)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    return 0.0


def parse_eta_from_tqdm(line: str) -> int:
    content = strip_log_prefix(line)
    m = re.search(r"<(\d+):(\d+):(\d+)", content)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m2 = re.search(r"<(\d+):(\d+)", content)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    m3 = re.search(r"<(\d+)s", content)
    if m3:
        return int(m3.group(1))
    return 0


def parse_algo_switch(line: str) -> str | None:
    content = strip_log_prefix(line)
    m = re.search(r"Algorithm:\s*(\w+)", content, re.IGNORECASE)
    return m.group(1) if m else None


def parse_result(line: str) -> AlgorithmResult | None:
    content = strip_log_prefix(line)
    m = re.search(r"\[(\w+)\]\s+reward=([-\d.]+)\+/-([-\d.]+)\s+time=([\d.]+)s", content, re.IGNORECASE)
    if m:
        return AlgorithmResult(
            algorithm=m.group(1),
            reward=float(m.group(2)),
            reward_std=float(m.group(3)),
            train_time=float(m.group(4)),
            source="log",
            status="finished",
        )
    m2 = re.search(r"\[(\w+)\].*?reward=([-\d.]+).*?time=([\d.]+)s", content, re.IGNORECASE)
    if m2:
        return AlgorithmResult(
            algorithm=m2.group(1),
            reward=float(m2.group(2)),
            reward_std=0,
            train_time=float(m2.group(3)),
            source="log",
            status="finished",
        )
    return None


def parse_update_count(line: str) -> int | None:
    content = strip_log_prefix(line)
    m = re.search(r"update_count=([\d.]+)", content, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    return None


def parse_env_from_algo_header(line: str) -> str | None:
    content = strip_log_prefix(line)
    m = re.search(r"Env:\s*(\S+)", content, re.IGNORECASE)
    return m.group(1) if m else None


def parse_benchmark_summary(line: str) -> bool:
    return "ALL ALGORITHMS COMPLETE" in line or "Benchmark finished" in line


def parse_algorithm_count_from_summary(line: str) -> int | None:
    content = strip_log_prefix(line)
    m = re.search(r"BENCHMARK\s+--\s+.*?\((\d+)\s+algorithms?\)", content, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def classify_log_line(line: str) -> str | None:
    lower = line.lower()
    if re.search(r"\b(error|exception|traceback|failed)\b", lower):
        return "error"
    if re.search(r"\b(warning|warn)\b", lower):
        return "warn"
    if (
        re.search(r"algorithm:", lower)
        or re.search(r"\breward=", lower)
        or re.search(r"\bbenchmark\b", lower)
        or re.search(r"\bfinished\b", lower)
        or re.search(r"\bcomplete\b", lower)
    ):
        return "info"
    return None


def parse_log_line(line: str, source_file: str = "") -> list[dict[str, Any]]:
    try:
        content = strip_log_prefix(line)
        events: list[dict[str, Any]] = []

        step_info = parse_step_from_tqdm(content)
        if step_info:
            current_step, total_step, it_per_sec = step_info
            events.append(
                {
                    "type": "progress",
                    "current_step": current_step,
                    "total_step": total_step,
                    "it_per_sec": it_per_sec,
                    "source_file": source_file,
                }
            )

        elapsed_seconds = parse_elapsed_from_tqdm(content)
        if elapsed_seconds > 0:
            events.append({"type": "elapsed", "elapsed_seconds": elapsed_seconds, "source_file": source_file})

        eta_seconds = parse_eta_from_tqdm(content)
        if eta_seconds > 0:
            events.append({"type": "eta", "eta_seconds": eta_seconds, "source_file": source_file})

        update_count = parse_update_count(content)
        if update_count is not None:
            events.append({"type": "update_count", "update_count": update_count, "source_file": source_file})

        algorithm = parse_algo_switch(content)
        if algorithm:
            events.append({"type": "algorithm_started", "algorithm": algorithm, "source_file": source_file})

        result = parse_result(content)
        if result:
            result_data = algorithm_result_to_dict(result)
            events.append({"type": "algorithm_finished", **result_data, "source_file": source_file})

        if parse_benchmark_summary(content):
            events.append({"type": "benchmark_finished", "message": content.strip(), "source_file": source_file})

        total_algorithms = parse_algorithm_count_from_summary(content)
        if total_algorithms is not None:
            events.append(
                {
                    "type": "algorithm_count",
                    "total_algorithms": total_algorithms,
                    "source_file": source_file,
                }
            )

        log_level = classify_log_line(content)
        if log_level:
            events.append(
                {
                    "type": "log",
                    "level": log_level,
                    "text": content.strip()[:300],
                    "source_file": source_file,
                }
            )

        return events
    except Exception:
        return []
