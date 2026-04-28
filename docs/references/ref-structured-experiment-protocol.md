# 结构化实验输出协议 — 实现参考

## 来源

- 项目：`rl-mec-dashboard`
- 关联文档：`docs/research-report.md`、`docs/architecture.md`、`docs/plan.md`
- 核心贡献：用结构化 `json/jsonl` 文件替代对训练日志的强依赖，使 dashboard 优先读取稳定协议，legacy 日志解析作为 fallback。

## 对应模块

- `docs/plan.md` 中的模块 3：结构化实验协议读取器
- `docs/plan.md` 中的模块 4：Run 发现与 benchmark JSON 补全
- `docs/plan.md` 中的模块 5：状态聚合器
- `docs/plan.md` 中的模块 6：状态存储、FastAPI 与 SSE 重构
- `docs/plan.md` 中的模块 10：文档与迁移说明

## 目录结构

dashboard 优先读取以下结构：

```text
runs/
└── <run_id>/
    ├── run_meta.json
    ├── events.jsonl
    ├── metrics.jsonl
    └── summary.json
```

读取优先级固定为：

1. structured run files：`runs/<run_id>/run_meta.json`、`events.jsonl`、`metrics.jsonl`、`summary.json`
2. legacy aggregate file：`results/benchmark.json`
3. legacy logs：`logs/benchmark*.log`、`logs/benchmark*.err.log`

## `run_meta.json`

用途：描述实验 run 的静态元信息和启动信息。

最小 schema：

```json
{
  "schema_version": 1,
  "run_id": "run_001",
  "created_at": "2026-04-28T15:30:00+08:00",
  "started_at": "2026-04-28T15:30:03+08:00",
  "finished_at": null,
  "status": "running",
  "environment": "MEC-v1",
  "algorithms": ["GRPO", "PPO"],
  "seeds": [0, 1],
  "config_hash": "testhash",
  "config_summary": {
    "total_steps": 500000,
    "num_users": 20,
    "num_edges": 5
  },
  "paper2_git_commit": null
}
```

实现要求：

- `schema_version` 固定为 `1`。
- `run_id` 必须稳定，不得在同一实验中变化。
- `config_summary` 只放 dashboard 需要展示的摘要，不放大体积对象。
- 缺失字段由 `dashboard.models.RunMeta` 默认值补齐。

## `events.jsonl`

用途：记录 run 生命周期事件、进度事件、算法切换、错误与关键日志。

每行一个 JSON object。支持事件类型：

### `algorithm_started`

```json
{"time":"2026-04-28T15:31:00+08:00","type":"algorithm_started","algorithm":"GRPO","message":"Algorithm: GRPO"}
```

状态聚合：

- 设置 `RunState.current_algorithm = algorithm`
- 不自动把上一个算法标记为完成；只有 `algorithm_finished` 才完成

### `progress`

```json
{"time":"2026-04-28T15:32:00+08:00","type":"progress","algorithm":"GRPO","current_step":12000,"total_step":500000,"it_per_sec":1020.5,"eta_seconds":478}
```

状态聚合：

- 更新 `current_step`
- 更新 `total_step`
- 更新 `it_per_sec`
- 更新 `eta_seconds`
- 计算 `progress_pct = current_step / total_step * 100`

### `algorithm_finished`

```json
{"time":"2026-04-28T15:40:00+08:00","type":"algorithm_finished","algorithm":"GRPO","reward":11.83,"reward_std":1.01,"train_time":325.8}
```

状态聚合：

- 构造 `AlgorithmResult`
- `source="structured"`
- `status="finished"`
- 加入 `RunState.results`
- 加入 `RunState.completed_algorithms`

### `log`

```json
{"time":"2026-04-28T15:41:00+08:00","type":"log","level":"warn","message":"High variance detected"}
```

状态聚合：

- 构造 `RecentLogEntry`
- 加入 `RunState.recent_logs`
- 只保留 `config.recent_log_limit` 条

### `error`

```json
{"time":"2026-04-28T15:42:00+08:00","type":"error","level":"error","message":"Parser failed for PPO seed 1"}
```

状态聚合：

- 加入 error log
- 设置 `RunState.last_error`
- 设置 `RunState.degraded = True`

### `benchmark_finished` / `run_finished`

```json
{"time":"2026-04-28T16:10:20+08:00","type":"run_finished","message":"Benchmark finished"}
```

状态聚合：

- 设置 `RunState.status = "finished"`

### `run_failed`

```json
{"time":"2026-04-28T16:10:20+08:00","type":"run_failed","message":"Training crashed"}
```

状态聚合：

- 设置 `RunState.status = "failed"`
- 设置 `RunState.last_error`

## `metrics.jsonl`

用途：记录时间序列指标，用于后续扩展曲线展示。

样例：

```json
{"time":"2026-04-28T15:32:00+08:00","algorithm":"GRPO","step":1000,"reward":1.2,"latency":0.32,"energy":0.81,"deadline_miss_rate":0.02,"throughput":15.3,"comm_score":0.71}
```

当前第一轮实现要求：

- `StructuredRunReader.read_metrics_tail(limit=1000)` 能读取尾部指标。
- API 第一轮不必须暴露完整指标曲线。
- 前端第一轮仍以 `summary.json` 和 `events.jsonl` 聚合结果为主。

## `summary.json`

用途：实验完成或阶段性写入最终结果，支持 dashboard 快速加载。

样例：

```json
{
  "schema_version": 1,
  "run_id": "run_001",
  "status": "finished",
  "started_at": "2026-04-28T15:30:03+08:00",
  "finished_at": "2026-04-28T16:10:20+08:00",
  "results": [
    {
      "algorithm": "GRPO",
      "reward": 11.8355,
      "reward_std": 1.0085,
      "train_time": 325.8,
      "latency": 0.12,
      "energy": 0.45,
      "deadline_miss_rate": 0.03,
      "throughput": 18.2,
      "comm_score": 0.76,
      "update_count": 481436
    }
  ]
}
```

映射到 `AlgorithmResult`：

- `algorithm` → `algorithm`
- `reward` → `reward`
- `reward_std` → `reward_std`
- `train_time` → `train_time`
- `latency` → `latency`
- `energy` → `energy`
- `deadline_miss_rate` → `deadline_miss_rate`
- `throughput` → `throughput`
- `comm_score` → `comm_score`
- `update_count` → `update_count`
- 固定 `source="structured"`
- 固定 `status="finished"`

## 异常处理

- 文件不存在：返回空结果，不抛 API 层异常。
- 单行 JSONL 损坏：跳过该行并将 run 标记为 degraded。
- 整个 JSON 文件损坏：reader 可抛 `ValueError`，由 `RunStateAggregator.scan_once()` 捕获并转为 degraded。
- dashboard 不得因单个 run 文件损坏导致整个 API 崩溃。

## Codex 实现注意事项

- 所有路径使用 `pathlib.Path`。
- JSONL 增量读取使用 byte offset。
- 如果文件被截断，offset 大于文件 size 时从 0 开始读。
- `events.jsonl` 的 `algorithm_finished` 要构造 `AlgorithmResult`，不要直接传 dict 到前端。
- structured result 优先级高于 legacy log result。
- legacy log result 缺失的字段可以从 `benchmark.json` 补齐。
