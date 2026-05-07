"""Controlled deletion of locally discovered dashboard source files."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from dashboard.config import DashboardConfig, backup_scan_roots
from dashboard.experiment_reader import safe_read_json_file
from dashboard.models import DeletePreview, DeleteResult, DeleteTarget
from dashboard.run_discovery import (
    discover_archive_only_backups,
    discover_benchmark_exports,
    discover_experiment_backups_from_roots,
    discover_runs,
    enrich_backup_figures,
)


DELETE_TOKEN_SALT = "dashboard-delete-v1"
RUNNING_STATUSES = {"running", "stop_requested"}
BLOCKED_DIR_NAMES = {".git", "docs", "dashboard", "tests", "scripts"}


class DeleteTargetNotFound(LookupError):
    pass


class DeleteBlocked(RuntimeError):
    pass


class DeleteTokenMismatch(RuntimeError):
    pass


class LocalDataDeleteService:
    def __init__(self, config: DashboardConfig):
        self.config = config

    def list_targets(self) -> list[DeleteTarget]:
        targets: list[DeleteTarget] = []
        claimed_paths: set[str] = set()

        descriptors = discover_runs(self.config)
        for descriptor in descriptors:
            if descriptor.experiment_dir is not None and not descriptor.is_placeholder:
                paths = self._claim_paths([descriptor.experiment_dir], claimed_paths)
                if paths:
                    blocked_reason = self._active_run_block_reason(descriptor.experiment_dir)
                    targets.append(
                        DeleteTarget(
                            target_id=f"active_run:{descriptor.run_id}",
                            target_type="active_run",
                            display_name=descriptor.display_name or descriptor.run_id,
                            source_run_id=descriptor.run_id,
                            paths=paths,
                            deletable=not blocked_reason,
                            blocked_reason=blocked_reason,
                        )
                    )

            if descriptor.run_dir is not None:
                paths = self._claim_paths([descriptor.run_dir], claimed_paths)
                if paths:
                    targets.append(
                        DeleteTarget(
                            target_id=f"structured_run:{descriptor.run_id}",
                            target_type="structured_run",
                            display_name=descriptor.display_name or descriptor.run_id,
                            source_run_id=descriptor.run_id,
                            paths=paths,
                        )
                    )

            log_paths = [descriptor.stdout_file]
            if descriptor.stderr_file != descriptor.stdout_file:
                log_paths.append(descriptor.stderr_file)
            paths = self._claim_paths(log_paths, claimed_paths)
            if paths:
                targets.append(
                    DeleteTarget(
                        target_id=f"legacy_log:{descriptor.run_id}",
                        target_type="legacy_log",
                        display_name=f"{descriptor.display_name or descriptor.run_id} logs",
                        source_run_id=descriptor.run_id,
                        paths=paths,
                    )
                )

        backups = discover_experiment_backups_from_roots(backup_scan_roots(self.config), self.config.results_dir)
        backups = enrich_backup_figures(backups, self.config.figures_dir)
        for backup in backups:
            paths = self._claim_paths(
                [backup.experiment_dir, backup.benchmark_archive_dir, backup.figures_archive_dir],
                claimed_paths,
            )
            if not paths:
                continue
            targets.append(
                DeleteTarget(
                    target_id=f"backup:{backup.backup_id}",
                    target_type="backup",
                    display_name=backup.display_name or backup.backup_id,
                    source_run_id=backup.source_run_id,
                    paths=paths,
                )
            )

        archive_backups = enrich_backup_figures(discover_archive_only_backups(self.config.results_dir), self.config.figures_dir)
        for backup in archive_backups:
            paths = self._claim_paths([backup.benchmark_archive_dir, backup.figures_archive_dir], claimed_paths)
            if not paths:
                continue
            targets.append(
                DeleteTarget(
                    target_id=f"archive:{backup.backup_id}",
                    target_type="archive",
                    display_name=backup.display_name or backup.backup_id,
                    source_run_id=backup.source_run_id,
                    paths=paths,
                )
            )

        for descriptor in descriptors:
            export_file = descriptor.benchmark_export_file
            if export_file is None or export_file.name == "benchmark.json" or not export_file.exists():
                continue
            paths = self._claim_paths([export_file], claimed_paths)
            if not paths:
                continue
            targets.append(
                DeleteTarget(
                    target_id=f"benchmark_export:{descriptor.run_id}",
                    target_type="benchmark_export",
                    display_name=f"{descriptor.run_id} benchmark export",
                    source_run_id=descriptor.run_id,
                    paths=paths,
                )
            )

        benchmark_json = Path(self.config.benchmark_json)
        if benchmark_json.exists():
            paths = self._claim_paths([benchmark_json], claimed_paths)
            if paths:
                targets.append(
                    DeleteTarget(
                        target_id="benchmark_json:latest",
                        target_type="benchmark_json",
                        display_name="Global benchmark.json",
                        paths=paths,
                    )
                )

        # M14-S5: benchmark-only export targets (mainline-a / direct scan)
        benchmark_descriptors = discover_benchmark_exports(self.config)
        for bd in benchmark_descriptors:
            if bd.benchmark_export_file is not None:
                paths = self._claim_paths([bd.benchmark_export_file], claimed_paths)
                if paths:
                    targets.append(
                        DeleteTarget(
                            target_id=f"benchmark_export:{bd.run_id}",
                            target_type="benchmark_export",
                            display_name=bd.display_name or bd.run_id,
                            source_run_id=bd.run_id,
                            paths=paths,
                        )
                    )

        # M14-S5: Global benchmark.json as benchmark_export target
        benchmark_json_target = Path(self.config.results_dir) / "benchmark.json"
        if benchmark_json_target.exists():
            paths = self._claim_paths([benchmark_json_target], claimed_paths)
            if paths:
                targets.append(
                    DeleteTarget(
                        target_id="benchmark_export:benchmark_json_latest",
                        target_type="benchmark_export",
                        display_name="Global Benchmark JSON",
                        source_run_id="benchmark_json_latest",
                        paths=paths,
                    )
                )

        return targets

    def preview_delete(self, target_id: str) -> DeletePreview:
        target = self._target_by_id(target_id)
        return self._preview_target(target)

    def confirm_delete(self, target_id: str, confirm_token: str) -> DeleteResult:
        preview = self.preview_delete(target_id)
        if confirm_token != preview.confirm_token:
            raise DeleteTokenMismatch("Invalid delete confirmation token")
        if preview.blocked:
            raise DeleteBlocked(preview.blocked_reason or "Delete target is blocked")

        deleted_paths: list[str] = []
        skipped_paths: list[str] = []
        errors: list[str] = []
        for path_text in sorted(preview.paths, key=lambda item: len(Path(item).parts), reverse=True):
            path = Path(path_text)
            if not path.exists():
                skipped_paths.append(path_text)
                continue
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                deleted_paths.append(path_text)
            except Exception as exc:
                errors.append(f"{path_text}: {exc}")
        return DeleteResult(target_id=target_id, deleted_paths=deleted_paths, skipped_paths=skipped_paths, errors=errors)

    def _preview_target(self, target: DeleteTarget) -> DeletePreview:
        paths = [str(Path(path).resolve(strict=False)) for path in target.paths if Path(path).exists()]
        blocked_reason = target.blocked_reason
        warnings = list(target.warnings)
        if not paths:
            blocked_reason = blocked_reason or "Delete target has no existing source paths"
        if not blocked_reason:
            blocked_reason = self._paths_block_reason(paths)

        total_files = 0
        total_dirs = 0
        total_bytes = 0
        if not blocked_reason:
            total_files, total_dirs, total_bytes = self._measure_paths(paths)

        blocked = bool(blocked_reason or not target.deletable)
        if blocked and not blocked_reason:
            blocked_reason = "Delete target is not deletable"
        confirm_token = "" if blocked else self._confirm_token(target.target_id, paths, total_bytes)
        return DeletePreview(
            target_id=target.target_id,
            target_type=target.target_type,
            display_name=target.display_name,
            paths=paths,
            total_files=total_files,
            total_dirs=total_dirs,
            total_bytes=total_bytes,
            blocked=blocked,
            blocked_reason=blocked_reason,
            confirm_token=confirm_token,
            warnings=warnings,
        )

    def _target_by_id(self, target_id: str) -> DeleteTarget:
        for target in self.list_targets():
            if target.target_id == target_id:
                return target
        raise DeleteTargetNotFound(target_id)

    def _allowed_roots(self) -> list[Path]:
        candidates: list[Path] = []
        if self.config.experiments_dir is not None:
            candidates.append(Path(self.config.experiments_dir))
        candidates.append(Path(self.config.logs_dir))
        if self.config.runs_dir is not None:
            candidates.append(Path(self.config.runs_dir))
        candidates.append(Path(self.config.results_dir))
        if self.config.figures_dir is not None:
            candidates.append(Path(self.config.figures_dir))
        candidates.extend(Path(path) for path in self.config.backup_scan_dirs)

        roots: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            resolved = candidate.resolve(strict=False)
            key = str(resolved).lower()
            if key in seen:
                continue
            seen.add(key)
            roots.append(resolved)
        return roots

    def _paths_block_reason(self, paths: list[str]) -> str:
        allowed_roots = self._allowed_roots()
        for path_text in paths:
            path = Path(path_text).resolve(strict=False)
            if not any(_is_strictly_inside(path, root) for root in allowed_roots):
                return f"Path is outside allowed roots: {path}"
            lower_parts = {part.lower() for part in path.parts}
            if ".git" in lower_parts:
                return f"Path contains a .git segment: {path}"
            blocked_parts = lower_parts.intersection(BLOCKED_DIR_NAMES)
            if blocked_parts:
                return f"Path contains blocked directory name: {sorted(blocked_parts)[0]}"
            nested_block = self._nested_blocked_path(path)
            if nested_block:
                return f"Path contains blocked nested directory: {nested_block}"
        return ""

    def _nested_blocked_path(self, path: Path) -> str:
        if not path.is_dir():
            return ""
        for item in path.rglob("*"):
            if item.is_dir() and item.name.lower() in BLOCKED_DIR_NAMES:
                return str(item)
        return ""

    def _active_run_block_reason(self, experiment_dir: Path) -> str:
        if (experiment_dir / "process.json").exists():
            return "active run has process.json marker"
        state_payload, _ = safe_read_json_file(experiment_dir / "state.json")
        if isinstance(state_payload, dict) and str(state_payload.get("status") or "") in RUNNING_STATUSES:
            return f"active run status is {state_payload.get('status')}"
        return ""

    def _claim_paths(self, values: list[str | Path], claimed_paths: set[str]) -> list[str]:
        paths: list[str] = []
        for value in values:
            if not value:
                continue
            path = Path(value)
            if not path.exists():
                continue
            resolved = str(path.resolve(strict=False))
            key = resolved.lower()
            if key in claimed_paths:
                continue
            claimed_paths.add(key)
            paths.append(resolved)
        return paths

    def _measure_paths(self, paths: list[str]) -> tuple[int, int, int]:
        total_files = 0
        total_dirs = 0
        total_bytes = 0
        for path_text in paths:
            path = Path(path_text)
            if path.is_file():
                total_files += 1
                total_bytes += path.stat().st_size
                continue
            if not path.is_dir():
                continue
            total_dirs += 1
            for item in path.rglob("*"):
                if item.is_dir():
                    total_dirs += 1
                elif item.is_file():
                    total_files += 1
                    total_bytes += item.stat().st_size
        return total_files, total_dirs, total_bytes

    def _confirm_token(self, target_id: str, paths: list[str], total_bytes: int) -> str:
        text = f"{target_id}|{sorted(paths)}|{total_bytes}|{DELETE_TOKEN_SALT}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_strictly_inside(path: Path, root: Path) -> bool:
    if path == root:
        return False
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
