# Structured Experiment Protocol

Dashboard 优先读取 paper2 训练端写出的结构化文件。没有这些文件时，dashboard 自动回退到 legacy logs 和 `benchmark.json`。

## Directory

```text
runs/
└── <run_id>/
    ├── run_meta.json
    ├── events.jsonl
    ├── metrics.jsonl
    └── summary.json
```

## Data Source Priority

1. `runs/<run_id>/run_meta.json`, `events.jsonl`, `metrics.jsonl`, `summary.json`
2. `results/benchmark.json`
3. `logs/benchmark*.log` and `logs/benchmark*.err.log`

## run_meta.json

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

## events.jsonl

每行一个 JSON object。支持 event types：

- `algorithm_started`
- `progress`
- `algorithm_finished`
- `log`
- `error`
- `benchmark_finished`
- `run_finished`
- `run_failed`

```jsonl
{"time":"2026-04-28T15:31:00+08:00","type":"algorithm_started","algorithm":"GRPO","message":"Algorithm: GRPO"}
{"time":"2026-04-28T15:32:00+08:00","type":"progress","algorithm":"GRPO","current_step":12000,"total_step":500000,"it_per_sec":1020.5,"eta_seconds":478}
{"time":"2026-04-28T15:40:00+08:00","type":"algorithm_finished","algorithm":"GRPO","reward":11.83,"reward_std":1.01,"train_time":325.8}
{"time":"2026-04-28T15:41:00+08:00","type":"log","level":"warn","message":"High variance detected"}
```

## metrics.jsonl

用于时间序列指标。第一轮 dashboard 读取 tail，主要为后续曲线扩展保留。

```jsonl
{"time":"2026-04-28T15:32:00+08:00","algorithm":"GRPO","step":1000,"reward":1.2,"latency":0.32,"energy":0.81,"deadline_miss_rate":0.02,"throughput":15.3,"comm_score":0.71}
{"time":"2026-04-28T15:33:00+08:00","algorithm":"GRPO","step":2000,"reward":1.8,"latency":0.30,"energy":0.79,"deadline_miss_rate":0.01,"throughput":16.1,"comm_score":0.73}
```

## summary.json

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

## Failure Handling

- Missing structured files do not fail the API.
- Broken JSON files mark the run degraded through the aggregator.
- Broken JSONL rows are skipped by the reader.
- Structured results take priority over legacy log and `benchmark.json` results.
