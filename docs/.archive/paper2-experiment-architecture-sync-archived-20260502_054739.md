# paper2 实验编排架构同步说明

## 新旧数据源对照

| 用途 | 新 paper2 协议 | legacy fallback |
|---|---|---|
| run 清单 | `experiments/<run_id>/run.json` | `runs/<run_id>/run_meta.json` |
| 实时状态 | `experiments/<run_id>/state.json` | `runs/<run_id>/events.jsonl` 或 `logs/benchmark*.log` |
| 进程 marker | `experiments/<run_id>/process.json` | 无 |
| 算法日志 | `experiments/<run_id>/artifacts/<ALGORITHM>/stdout.log`、`stderr.log` | `logs/benchmark*.log`、`.err.log` |
| 算法结果 | `experiments/<run_id>/artifacts/<ALGORITHM>/result.json` | `runs/<run_id>/summary.json` |
| 图表导出 | `results/benchmark_<run_id>.json` | `results/benchmark.json` |

Dashboard 不读取、不依赖 `experiments/.index.sqlite3`。

## 实时状态源

state.json 是唯一实时状态源。

`experiments/<run_id>/state.json` 是唯一实时状态源。Dashboard 不使用 `results/benchmark.json` 或 `results/benchmark_<run_id>.json` 判断实验是否 running、failed、completed。

算法表顺序来自 `run.json.algorithms`；状态来自 `state.json.records[]`。`stderr.log` 非空不代表失败，失败只由 `record.status` 和 `record.error` 表达。`record.status == "running"` 时，旧的 `error`、`exit_code`、`finished_at` 残留不会作为当前失败展示。

## Artifact 日志路径

每个算法固定读取：

```text
experiments/<run_id>/artifacts/<ALGORITHM>/stdout.log
experiments/<run_id>/artifacts/<ALGORITHM>/stderr.log
```

日志 API 只返回 tail 文本，前端使用 `textContent` 展示，不执行日志内容。

## Benchmark Export

`results/benchmark_<run_id>.json` 只用于图表和兼容导出。它可以补充已完成算法的 latency、energy、comm score 等指标，但不能覆盖 `artifacts/<ALGORITHM>/result.json` 中已有的 structured 结果，也不能决定当前实验状态。

空数组 `[]` 是合法状态，表示暂无已完成算法结果。

## 只读边界

Dashboard 本轮保持只读：

- 不启动训练。
- 不停止、kill 或 reset 训练进程。
- 不删除 `experiments/`、`results/`、`logs/` 中的文件。
- 不通过前端代理 paper2 的 start/stop/reset/export 操作。

## 验收用例

### Full 17 running

输入：

```text
experiments/paper2_full_17_vscode/run.json
experiments/paper2_full_17_vscode/state.json
```

期望：

- 页面显示 17 个算法。
- 算法顺序为 GRPO, PPO, SAC, DDQN, DDPG, TD3, A3C, TRPO, SimPO, MAPPO, QMIX, COMA, IPPO, VDN, MADDPG, IQL, MATD3。
- 当前算法来自 `records[current_index]`。
- 进度按 `completed_algorithms.length / records.length` 计算。
- 当前算法可打开 stdout/stderr。

### Quick failed

输入：

```text
experiments/vscode_quick/state.json
experiments/vscode_quick/artifacts/GRPO/stdout.log
experiments/vscode_quick/artifacts/GRPO/stderr.log
```

期望：

- 页面显示 Quick 共有 3 个算法。
- GRPO failed 显示错误摘要。
- 错误详情提供 stdout/stderr 链接。
- PPO/SAC 保持 pending。
- Quick smoke test 不作为正式论文结果展示。

### Empty benchmark

输入：

```json
[]
```

期望：

- 图表页显示“暂无已完成算法结果”。
- 不把空数组视为加载失败。

### Running stale error

输入：

```json
{
  "name": "GRPO",
  "status": "running",
  "exit_code": 1,
  "error": "previous failed attempt"
}
```

期望：

- UI 显示 GRPO running。
- 不把旧 `error` 当作当前失败。
- `attempts > 1` 可作为调试信息展示。
