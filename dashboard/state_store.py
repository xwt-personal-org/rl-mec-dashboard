"""In-memory dashboard state store."""

from __future__ import annotations

import copy
import threading
from dashboard.config import DashboardConfig
from dashboard.models import RunDescriptor, RunState, RunSummary
from dashboard.run_discovery import discover_runs
from dashboard.state_aggregator import RunStateAggregator

COMPARE_METRICS = {
    "reward",
    "latency",
    "energy",
    "deadline_miss_rate",
    "throughput",
    "comm_score",
    "train_time",
    "update_count",
}


class DashboardStateStore:
    def __init__(self, config: DashboardConfig, aggregator: RunStateAggregator):
        self.config = config
        self.aggregator = aggregator
        self._lock = threading.RLock()
        self._run_descriptors: dict[str, RunDescriptor] = {}
        self._run_states: dict[str, RunState] = {}
        self._scanner_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def refresh_run_index(self) -> list[RunDescriptor]:
        descriptors = discover_runs(self.config)
        with self._lock:
            self._run_descriptors = {descriptor.run_id: descriptor for descriptor in descriptors}
        return list(descriptors)

    def ensure_run_state(self, run_id: str) -> RunState:
        with self._lock:
            if run_id in self._run_states:
                return self._run_states[run_id]
            descriptor = self._run_descriptors.get(run_id)
            if descriptor is None:
                self.refresh_run_index()
                descriptor = self._run_descriptors.get(run_id)
            if descriptor is None:
                state = RunState(run_id=run_id)
            else:
                state = self.aggregator.initialize_state(descriptor)
            self._run_states[run_id] = state
            return state

    def get_runs(self) -> list[RunSummary]:
        with self._lock:
            summaries = []
            for descriptor in self._run_descriptors.values():
                state = self._run_states.get(descriptor.run_id)
                if state is None:
                    state = self.aggregator.initialize_state(descriptor)
                    self._run_states[descriptor.run_id] = state
                summaries.append(_summary_from_state(descriptor, state))
            summaries.sort(key=lambda summary: summary.updated_at, reverse=True)
            return copy.deepcopy(summaries)

    def get_run_state(self, run_id: str) -> RunState | None:
        with self._lock:
            state = self._run_states.get(run_id)
            return copy.deepcopy(state) if state is not None else None

    def get_compare_payload(self, run_ids: list[str], metric: str) -> dict:
        if metric not in COMPARE_METRICS:
            raise ValueError(f"Unsupported compare metric: {metric}")
        with self._lock:
            selected_ids = run_ids or [summary.run_id for summary in self.get_runs()]
            states = [self._run_states[run_id] for run_id in selected_ids if run_id in self._run_states]

        algorithms = sorted({result.algorithm for state in states for result in state.results})
        series = []
        for algorithm in algorithms:
            values = []
            for state in states:
                result = next((item for item in state.results if item.algorithm == algorithm), None)
                values.append(
                    {
                        "run_id": state.run_id,
                        "value": getattr(result, metric) if result is not None else None,
                    }
                )
            series.append({"algorithm": algorithm, "values": values})

        return {
            "metric": metric,
            "run_ids": [state.run_id for state in states],
            "algorithms": algorithms,
            "series": series,
        }

    def scan_all_once(self) -> None:
        descriptors = self.refresh_run_index()
        with self._lock:
            for descriptor in descriptors:
                state = self.ensure_run_state(descriptor.run_id)
                self._run_states[descriptor.run_id] = self.aggregator.scan_once(descriptor, state)

    def start_background_scan(self) -> None:
        with self._lock:
            if self._scanner_thread and self._scanner_thread.is_alive():
                return
            self._stop_event.clear()
            self._scanner_thread = threading.Thread(target=self._scan_loop, daemon=True)
            self._scanner_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        thread = self._scanner_thread
        if thread and thread.is_alive():
            thread.join(timeout=2)

    def _scan_loop(self) -> None:
        while not self._stop_event.is_set():
            self.scan_all_once()
            self._stop_event.wait(self.config.scan_interval_sec)


def _summary_from_state(descriptor: RunDescriptor, state: RunState) -> RunSummary:
    return RunSummary(
        run_id=state.run_id,
        display_name=descriptor.display_name or state.run_id,
        status=state.status,
        current_algorithm=state.current_algorithm,
        progress_pct=state.progress_pct,
        overall_progress=state.overall_progress,
        total_algorithms=state.total_algorithms,
        updated_at=state.updated_at,
        source_type=state.source_type,
        has_error=bool(state.last_error or state.degraded),
        last_error=state.last_error,
    )
