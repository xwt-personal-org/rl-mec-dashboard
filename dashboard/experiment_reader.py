"""Read paper2 experiment files without mutating training output."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from dashboard.models import (
    AlgorithmResult,
    AlgorithmRunRecord,
    AlgorithmSpec,
    ExperimentRunManifest,
    ExperimentStateSnapshot,
)


def safe_read_json_file(path: Path) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    path = Path(path)
    if not path.exists():
        return None, None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return None, str(exc)
    if not text.strip():
        return None, f"empty json file: {path}"
    try:
        payload = json.loads(text)
    except JSONDecodeError:
        return None, f"invalid json file: {path}"
    if isinstance(payload, (dict, list)):
        return payload, None
    return None, f"invalid json file: {path}"


def read_text_tail(path: Path, max_bytes: int = 65536) -> tuple[str, bool]:
    path = Path(path)
    if not path.exists():
        return "", False
    size = path.stat().st_size
    with path.open("rb") as f:
        if max_bytes > 0 and size > max_bytes:
            f.seek(-max_bytes, 2)
        data = f.read()
    return data.decode("utf-8", errors="replace"), True


class Paper2ExperimentReader:
    def __init__(self, experiment_dir: Path):
        self.experiment_dir = Path(experiment_dir)
        self.run_json_path = self.experiment_dir / "run.json"
        self.state_json_path = self.experiment_dir / "state.json"
        self.process_json_path = self.experiment_dir / "process.json"
        self.artifacts_dir = self.experiment_dir / "artifacts"

    def exists(self) -> bool:
        return self.run_json_path.exists() or self.state_json_path.exists()

    def artifact_base(self, algorithm: str) -> Path:
        return self.artifacts_dir / algorithm

    def stdout_path(self, algorithm: str) -> Path:
        return self.artifact_base(algorithm) / "stdout.log"

    def stderr_path(self, algorithm: str) -> Path:
        return self.artifact_base(algorithm) / "stderr.log"

    def default_result_path(self, algorithm: str) -> Path:
        return self.artifact_base(algorithm) / "result.json"

    def read_run_manifest(self) -> tuple[ExperimentRunManifest | None, str | None]:
        payload, error = safe_read_json_file(self.run_json_path)
        if error or not isinstance(payload, dict):
            return None, error

        run_id = str(payload.get("run_id") or self.experiment_dir.name)
        algorithms = []
        for item in payload.get("algorithms", []):
            spec = _algorithm_spec_from_payload(item)
            if spec is not None:
                algorithms.append(spec)

        return (
            ExperimentRunManifest(
                schema_version=int(payload.get("schema_version", 1) or 1),
                run_id=run_id,
                name=str(payload.get("name") or run_id),
                created_at=str(payload.get("created_at", "")),
                updated_at=str(payload.get("updated_at", "")),
                algorithms=algorithms,
                project_root=str(payload.get("project_root", "")),
                output_dir=str(payload.get("output_dir", "")),
                experiment_dir=str(payload.get("experiment_dir", self.experiment_dir)),
                metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata", {}), dict) else {},
            ),
            None,
        )

    def read_state_snapshot(
        self,
        manifest: ExperimentRunManifest | None = None,
    ) -> tuple[ExperimentStateSnapshot | None, str | None]:
        payload, error = safe_read_json_file(self.state_json_path)
        if error:
            return None, error
        if not isinstance(payload, dict):
            if manifest is None:
                return None, None
            payload = {}

        run_id = str(payload.get("run_id") or (manifest.run_id if manifest else self.experiment_dir.name))
        raw_records = payload.get("records", [])
        records: list[AlgorithmRunRecord] = []
        if isinstance(raw_records, list):
            for item in raw_records:
                record = self._record_from_payload(item)
                if record is not None:
                    records.append(record)
        if not records and manifest is not None:
            records = [self._record_from_payload({"name": spec.name}) for spec in manifest.algorithms]
            records = [record for record in records if record is not None]

        return (
            ExperimentStateSnapshot(
                schema_version=int(payload.get("schema_version", 1) or 1),
                run_id=run_id,
                status=str(payload.get("status", "initialized")),
                current_index=int(payload.get("current_index", 0) or 0),
                records=records,
                completed_algorithms=[str(item) for item in payload.get("completed_algorithms", [])],
                stop_requested=bool(payload.get("stop_requested", False)),
                last_error=payload.get("last_error"),
                updated_at=str(payload.get("updated_at", "")),
            ),
            None,
        )

    def _record_from_payload(self, payload: Any) -> AlgorithmRunRecord | None:
        if isinstance(payload, str):
            payload = {"name": payload}
        if not isinstance(payload, dict):
            return None
        name = payload.get("name") or payload.get("algorithm")
        if not name:
            return None
        algorithm = str(name)
        result_path = str(payload.get("result_path") or self.default_result_path(algorithm))
        return AlgorithmRunRecord(
            name=algorithm,
            status=str(payload.get("status", "pending")),
            attempts=int(payload.get("attempts", 0) or 0),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            exit_code=_optional_int(payload.get("exit_code")),
            device=str(payload.get("device", "")),
            result_path=result_path,
            checkpoint_dir=str(payload.get("checkpoint_dir", "")),
            stdout_path=str(self.stdout_path(algorithm)),
            stderr_path=str(self.stderr_path(algorithm)),
            error=payload.get("error"),
            result_missing=bool(payload.get("result_missing", False)),
        )

    def read_algorithm_result(self, record: AlgorithmRunRecord) -> tuple[AlgorithmResult | None, str | None]:
        if record.status != "completed":
            return None, None
        result_path = self.resolve_artifact_path(record.result_path, record.name)
        payload, error = safe_read_json_file(result_path)
        if error:
            return None, error
        if payload is None:
            return None, f"result file missing: {result_path}"
        if not isinstance(payload, dict):
            return None, f"invalid result file: {result_path}"

        final_eval = payload.get("final_eval", {})
        if not isinstance(final_eval, dict):
            final_eval = {}
        return (
            AlgorithmResult(
                algorithm=str(payload.get("algorithm") or record.name),
                reward=_optional_float(final_eval.get("eval/reward_mean")),
                reward_std=_optional_float(final_eval.get("eval/reward_std")),
                latency=_optional_float(final_eval.get("eval/latency_mean")),
                energy=_optional_float(final_eval.get("eval/energy_mean")),
                comm_score=_optional_float(final_eval.get("eval/comm_score")),
                environment=str(payload.get("environment", "")),
                seed=_optional_int(payload.get("seed")),
                device=str(payload.get("device", record.device)),
                train_timesteps=_optional_int(payload.get("train_timesteps")),
                checkpoint_dir=str(payload.get("checkpoint_dir", record.checkpoint_dir)),
                result_path=str(result_path),
                final_eval=dict(final_eval),
                source="structured",
                status="finished",
            ),
            None,
        )

    def resolve_artifact_path(self, path_value: str, algorithm: str) -> Path:
        if not path_value:
            return self.default_result_path(algorithm)
        path = Path(path_value.replace("\\", "/"))
        if path.is_absolute():
            return path
        parts = path.parts
        if parts and parts[0] == "experiments":
            return self.experiment_dir.parent.parent / path
        if parts and parts[0] == self.experiment_dir.name:
            return self.experiment_dir.parent / path
        return self.experiment_dir / path


def _algorithm_spec_from_payload(payload: Any) -> AlgorithmSpec | None:
    if isinstance(payload, str):
        return AlgorithmSpec(name=payload)
    if not isinstance(payload, dict):
        return None
    name = payload.get("name") or payload.get("algorithm")
    if not name:
        return None
    extra_args = payload.get("extra_args", [])
    if not isinstance(extra_args, list):
        extra_args = []
    return AlgorithmSpec(
        name=str(name),
        config_path=str(payload.get("config_path", "")),
        timesteps=_optional_int(payload.get("timesteps")),
        seed=_optional_int(payload.get("seed")),
        device=str(payload.get("device", "")),
        env=str(payload.get("env", "")),
        eval_episodes=_optional_int(payload.get("eval_episodes")),
        extra_args=[str(item) for item in extra_args],
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
