# paper2 Dashboard Writer Reference

本文档是 paper2 训练端集成参考。`rl-mec-dashboard` 仓库只读取输出文件，不直接控制训练，不启动训练，不停止训练，也不调用 paper2 训练函数。

## Role

`DashboardRunWriter` 应放在 paper2 训练项目中，由训练进程主动写出 structured protocol 文件：

```text
runs/<run_id>/
├── run_meta.json
├── events.jsonl
├── metrics.jsonl
└── summary.json
```

Dashboard 仍保留 legacy fallback：没有 writer 输出时继续读取 `logs/benchmark*.log`、`logs/benchmark*.err.log` 和 `results/benchmark.json`。

## Pseudocode

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class DashboardRunWriter:
    def __init__(self, run_dir: Path, run_id: str, config_summary: dict):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.config_summary = config_summary
        self.meta_path = self.run_dir / "run_meta.json"
        self.events_path = self.run_dir / "events.jsonl"
        self.metrics_path = self.run_dir / "metrics.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_json_atomic(self, path: Path, payload: dict) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()

    def write_meta(self, meta: dict) -> None:
        payload = {
            "schema_version": 1,
            "run_id": self.run_id,
            "created_at": self._now(),
            "started_at": meta.get("started_at"),
            "finished_at": meta.get("finished_at"),
            "status": meta.get("status", "running"),
            "environment": meta.get("environment", ""),
            "algorithms": meta.get("algorithms", []),
            "seeds": meta.get("seeds", []),
            "config_hash": meta.get("config_hash", ""),
            "config_summary": self.config_summary,
            "paper2_git_commit": meta.get("paper2_git_commit"),
        }
        self._write_json_atomic(self.meta_path, payload)

    def append_event(self, event: dict) -> None:
        self._append_jsonl(self.events_path, {"time": self._now(), **event})

    def append_metric(self, metric: dict) -> None:
        self._append_jsonl(self.metrics_path, {"time": self._now(), **metric})

    def write_summary(self, summary: dict) -> None:
        self._write_json_atomic(self.summary_path, {"schema_version": 1, "run_id": self.run_id, **summary})

    def mark_finished(self) -> None:
        self.append_event({"type": "run_finished", "message": "Benchmark finished"})

    def mark_failed(self, error: str) -> None:
        self.append_event({"type": "run_failed", "level": "error", "message": error})
```

## Integration Notes

- Call `write_meta()` when a benchmark run starts.
- Call `append_event({"type": "algorithm_started", ...})` when an algorithm starts.
- Call `append_event({"type": "progress", ...})` at a coarse interval such as once per second.
- Call `append_metric()` for sampled reward, latency, energy, deadline miss, throughput, and comm score values.
- Call `append_event({"type": "algorithm_finished", ...})` when an algorithm completes.
- Call `write_summary()` and `mark_finished()` at normal completion.
- Call `mark_failed()` and write a failed summary if training crashes.

The writer is append-only for JSONL files. Summary writes should be atomic through temporary file replacement.
