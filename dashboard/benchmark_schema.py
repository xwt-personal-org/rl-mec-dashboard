"""Benchmark schema adapter for Mainline-A and legacy benchmark JSON formats."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard.models import AlgorithmResult


class BenchmarkSchemaAdapter:
    """Normalize benchmark JSON items into AlgorithmResult, preserving unknown fields."""

    # Known Mainline-A field names
    MAINLINE_A_FIELDS = {
        "evidence_level", "boundary_note", "oracle_gap", "composite_score",
        "constraint_violation_rate", "deadline_violation_rate",
        "scenario", "stage", "environment", "train_timesteps", "device", "seed", "status"
    }

    # Standard legacy field names that map to AlgorithmResult
    STANDARD_FIELDS = {
        "algorithm", "final_reward_mean", "final_reward_mean_mean",
        "final_reward_std", "final_reward_mean_std",
        "train_time_seconds_mean", "final_latency_mean", "final_latency_mean_mean",
        "final_energy_mean", "final_energy_mean_mean",
        "final_deadline_miss_rate_mean", "final_throughput_tasks_per_step_mean",
        "final_comm_score", "final_comm_score_mean",
        "total_updates_mean", "checkpoint_dir", "result_path", "convergence_by_seed"
    }

    # Evidence level inference rules: (pattern, label)
    _EVIDENCE_PATTERNS = (
        (re.compile(r"\bn3\b", re.IGNORECASE), "OOD formal execution evidence"),
        (re.compile(r"\bood\b", re.IGNORECASE), "OOD formal execution evidence"),
        (re.compile(r"\bn2\b", re.IGNORECASE), "deterministic controlled probe only"),
        (re.compile(r"\bn1\b", re.IGNORECASE), "small-scale oracle evidence"),
        (re.compile(r"\bn0\b", re.IGNORECASE), "smoke evidence"),
    )

    def detect_schema(self, payload: Any) -> str:
        """Detect schema type: 'mainline_a' or 'legacy'."""
        if isinstance(payload, list) and payload:
            for item in payload:
                if isinstance(item, dict):
                    if any(k in item for k in ("evidence_level", "boundary_note", "oracle_gap", "composite_score")):
                        return "mainline_a"
            return "legacy"
        return "legacy"

    def normalize_item(self, item: dict[str, Any], source_path: Path | None = None) -> AlgorithmResult:
        """Convert raw benchmark JSON item to AlgorithmResult."""
        algorithm = item.get("algorithm")
        if not algorithm:
            algorithm = "unknown"
        algorithm = str(algorithm)

        # Standard field extraction (matching load_benchmark_results pattern)
        reward = _optional_float(_first_value(item.get("final_reward_mean"), item.get("final_reward_mean_mean")))
        reward_std = _optional_float(_first_value(item.get("final_reward_std"), item.get("final_reward_mean_std")))
        train_time = _optional_float(item.get("train_time_seconds_mean"))
        latency = _optional_float(_first_value(item.get("final_latency_mean"), item.get("final_latency_mean_mean")))
        energy = _optional_float(_first_value(item.get("final_energy_mean"), item.get("final_energy_mean_mean")))
        deadline_miss_rate = _optional_float(item.get("final_deadline_miss_rate_mean"))
        throughput = _optional_float(item.get("final_throughput_tasks_per_step_mean"))
        comm_score = _optional_float(_first_value(item.get("final_comm_score"), item.get("final_comm_score_mean")))
        update_count = _optional_int(item.get("total_updates_mean"))

        # Mainline-A specific fields
        scenario = str(item.get("scenario", ""))
        stage = str(item.get("stage", ""))
        evidence_level = str(item.get("evidence_level", ""))
        boundary_note = str(item.get("boundary_note", ""))
        composite_score = _optional_float(item.get("composite_score"))
        oracle_gap = _optional_float(item.get("oracle_gap"))
        constraint_violation_rate = _optional_float(item.get("constraint_violation_rate"))
        deadline_violation_rate = _optional_float(item.get("deadline_violation_rate"))

        # Infer evidence_level if not set
        if not evidence_level:
            evidence_level = self._infer_evidence_level(item, source_path)

        # Collect unknown fields into raw_metrics
        all_known = self.STANDARD_FIELDS | self.MAINLINE_A_FIELDS
        raw_metrics: dict[str, Any] = {}
        for key, value in item.items():
            if key not in all_known:
                raw_metrics[key] = value

        return AlgorithmResult(
            algorithm=algorithm,
            reward=reward,
            reward_std=reward_std,
            train_time=train_time,
            latency=latency,
            energy=energy,
            deadline_miss_rate=deadline_miss_rate,
            throughput=throughput,
            comm_score=comm_score,
            update_count=update_count,
            environment=str(item.get("environment", "")),
            seed=_optional_int(item.get("seed")),
            device=str(item.get("device", "")),
            train_timesteps=_optional_int(item.get("train_timesteps")),
            checkpoint_dir=str(item.get("checkpoint_dir", "")),
            result_path=str(item.get("result_path", "")),
            source="benchmark_json",
            status=str(item.get("status") or "historical"),
            scenario=scenario,
            stage=stage,
            evidence_level=evidence_level,
            boundary_note=boundary_note,
            composite_score=composite_score,
            oracle_gap=oracle_gap,
            deadline_violation_rate=deadline_violation_rate,
            constraint_violation_rate=constraint_violation_rate,
            raw_metrics=raw_metrics,
        )

    def _infer_evidence_level(self, item: dict[str, Any], source_path: Path | None) -> str:
        """Infer evidence level from filename or payload content."""
        filename = ""
        if source_path is not None:
            filename = source_path.name.lower()

        # Check filename patterns first
        for pattern, label in self._EVIDENCE_PATTERNS:
            if pattern.search(filename):
                return label

        # Check payload content for evidence hints
        payload_str = str(item).lower()
        for pattern, label in self._EVIDENCE_PATTERNS:
            if pattern.search(payload_str):
                return label

        # Default rule for known benchmark file without evidence field
        if source_path is not None and "benchmark_direct_all_17_vscode" in source_path.name.lower():
            return "benchmark evidence pending review"

        return ""

    def extract_run_metadata(self, payload: Any, source_path: Path) -> dict[str, Any]:
        """Extract run-level metadata from benchmark payload."""
        algorithms: list[str] = []
        has_evidence_fields = False
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    alg = item.get("algorithm")
                    if alg:
                        algorithms.append(str(alg))
                    if not has_evidence_fields and any(
                        k in item for k in ("evidence_level", "boundary_note", "oracle_gap", "composite_score")
                    ):
                        has_evidence_fields = True

        schema = self.detect_schema(payload)
        return {
            "source_type": "mainline_a_benchmark" if schema == "mainline_a" else "benchmark_export",
            "total_algorithms": len(algorithms),
            "algorithms": algorithms,
            "has_evidence_fields": has_evidence_fields,
        }


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(float(value))
