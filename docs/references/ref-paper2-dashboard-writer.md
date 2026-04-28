# paper2 Dashboard Writer — 实现参考

## 来源

- 项目：`paper2` 与 `rl-mec-dashboard` 集成规划
- 关联文档：`docs/architecture.md`、`docs/plan.md`
- 核心贡献：为 paper2 训练端提供一个轻量 writer，使训练过程额外输出 dashboard 友好的结构化文件；dashboard 仍保持只读，不直接控制训练。

## 对应模块

- `docs/plan.md` 中的模块 3：结构化实验协议读取器
- `docs/plan.md` 中的模块 10：文档与迁移说明
- 本参考主要服务于后续 paper2 侧集成，不要求 `rl-mec-dashboard` 第一轮直接修改 paper2 主训练逻辑。

## 设计原则

1. dashboard 只读。
   - writer 由 paper2 训练进程调用。
   - dashboard 只读取 writer 输出文件。
2. writer 不依赖 FastAPI。
   - paper2 训练端只需要标准库即可写文件。
3. 每次写入保持 append-only。
   - `events.jsonl` 与 `metrics.jsonl` 每行一个 JSON。
   - summary 可覆盖写。
4. 写入必须尽量抗中断。
   - JSONL 每次 append 后 flush。
   - summary 写入建议使用临时文件 + rename。

## 建议目录

```text
paper2/
└── runs/
    └── <run_id>/
        ├── run_meta.json
        ├── events.jsonl
        ├── metrics.jsonl
        └── summary.json
```

## 参考类定义

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DashboardRunWriter:
    def __init__(self, run_dir: Path, run_id: str, config_summary: dict[str, Any]):
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

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()

    def write_meta(self, meta: dict[str, Any]) -> None:
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

    def append_event(self, event: dict[str, Any]) -> None:
        payload = {"time": self._now(), **event}
        self._append_jsonl(self.events_path, payload)

    def append_metric(self, metric: dict[str, Any]) -> None:
        payload = {"time": self._now(), **metric}
        self._append_jsonl(self.metrics_path, payload)

    def write_summary(self, summary: dict[str, Any]) -> None:
        payload = {
            "schema_version": 1,
            "run_id": self.run_id,
            **summary,
        }
        self._write_json_atomic(self.summary_path, payload)

    def mark_finished(self) -> None:
        self.append_event({
            "type": "run_finished",
            "message": "Benchmark finished",
        })

    def mark_failed(self, error: str) -> None:
        self.append_event({
            "type": "run_failed",
            "level": "error",
            "message": error,
        })
```

## paper2 训练流程接入点

### 1. run 启动时

```python
writer = DashboardRunWriter(
    run_dir=Path("runs") / run_id,
    run_id=run_id,
    config_summary={
        "total_steps": total_steps,
        "num_users": num_users,
        "num_edges": num_edges,
    },
)
writer.write_meta({
    "started_at": now_iso,
    "status": "running",
    "environment": env_name,
    "algorithms": algorithms,
    "seeds": seeds,
    "config_hash": config_hash,
    "paper2_git_commit": git_commit,
})
```

### 2. 算法开始时

```python
writer.append_event({
    "type": "algorithm_started",
    "algorithm": algo_name,
    "message": f"Algorithm: {algo_name}",
})
```

### 3. 训练进度更新时

```python
writer.append_event({
    "type": "progress",
    "algorithm": algo_name,
    "current_step": current_step,
    "total_step": total_step,
    "it_per_sec": it_per_sec,
    "eta_seconds": eta_seconds,
})
```

建议频率：

- 每 1 秒一次，或每 N 个 step 一次。
- 不要每个 step 都写事件，避免 JSONL 过大。

### 4. 指标采样时

```python
writer.append_metric({
    "algorithm": algo_name,
    "step": current_step,
    "reward": reward,
    "latency": latency,
    "energy": energy,
    "deadline_miss_rate": deadline_miss_rate,
    "throughput": throughput,
    "comm_score": comm_score,
})
```

### 5. 算法完成时

```python
writer.append_event({
    "type": "algorithm_finished",
    "algorithm": algo_name,
    "reward": final_reward_mean,
    "reward_std": final_reward_std,
    "train_time": train_time_seconds,
    "latency": final_latency,
    "energy": final_energy,
    "deadline_miss_rate": final_deadline_miss_rate,
    "throughput": final_throughput,
    "comm_score": final_comm_score,
    "update_count": total_updates,
})
```

### 6. benchmark 完成时

```python
writer.write_summary({
    "status": "finished",
    "started_at": started_at,
    "finished_at": finished_at,
    "results": results,
})
writer.mark_finished()
```

### 7. 训练失败时

```python
writer.mark_failed(str(exc))
writer.write_summary({
    "status": "failed",
    "started_at": started_at,
    "finished_at": now_iso,
    "results": partial_results,
    "last_error": str(exc),
})
```

## 与 legacy 模式的关系

- 没有 writer 时，dashboard 继续读取：
  - `logs/benchmark*.log`
  - `logs/benchmark*.err.log`
  - `results/benchmark.json`
- 有 writer 时，dashboard 优先读取：
  - `runs/<run_id>/run_meta.json`
  - `runs/<run_id>/events.jsonl`
  - `runs/<run_id>/metrics.jsonl`
  - `runs/<run_id>/summary.json`
- 同一个 `run_id` 同时有 structured 与 legacy 文件时，dashboard 将其视为 `mixed` run，并按 structured 优先级合并结果。

## Codex 实现注意事项

- 不要在 `rl-mec-dashboard` 中实现训练控制。
- 不要让 dashboard 调用 paper2 的训练函数。
- paper2 writer 只是后续集成参考，第一轮可以只在 `docs/paper2-dashboard-writer-reference.md` 中落文档。
- 如果后续真正改 paper2，应在 paper2 仓库中新增 writer，不应把 writer 与 dashboard server 耦合。
