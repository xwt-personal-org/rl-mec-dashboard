# RL-MEC Training Dashboard

轻量级网页看板，用于实时监控 RL-MEC Benchmark 训练任务状态。Dashboard 只读训练输出文件，不启动、不停止、不重启 paper2 训练任务。

## 功能

- 实时状态监控：当前算法、训练进度、速度、ETA、日志摘要。
- 多运行总览：支持 legacy logs、structured runs 和 mixed runs。
- 结构化协议优先：优先读取 `runs/<run_id>/` 下的 JSON/JSONL 文件。
- Legacy fallback：没有 structured runs 时继续读取 `logs/benchmark*.log` 和 `results/benchmark.json`。
- 多实验对比：`/api/compare` 支持按 reward、latency、energy 等指标对比。
- 结果导出：支持 CSV 和 Markdown 表格导出。
- SSE 实时推送：前端通过 Server-Sent Events 刷新 run snapshot。
- Stop Dashboard Server：只关闭 dashboard server，不停止训练任务。

## 启动方式

### 命令行

Legacy 模式保持兼容：

```bash
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json \
    --host 127.0.0.1 --port 8088
```

Structured 模式增加可选 `--runs-dir`：

```bash
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json \
    --runs-dir C:\Users\22003\paper2\paper2\runs \
    --host 127.0.0.1 --port 8088
```

访问：`http://127.0.0.1:8088`

### Windows 启动脚本

- `start_dashboard.vbs`：静默启动并打开浏览器。
- `start_dashboard.bat`：底层启动脚本。

页面上的 `Stop Dashboard Server` 只关闭 dashboard server；它不停止训练、不清理训练进程、不修改 paper2 输出。

## 数据源优先级

1. Structured run files：`runs/<run_id>/run_meta.json`、`events.jsonl`、`metrics.jsonl`、`summary.json`
2. Legacy aggregate file：`results/benchmark.json`
3. Legacy logs：`logs/benchmark*.log`、`logs/benchmark*.err.log`

详见：

- `docs/structured-protocol.md`
- `docs/paper2-dashboard-writer-reference.md`

## API

- `GET /api/health`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `GET /api/compare?run_ids=a,b&metric=reward`
- `GET /api/export/results.csv?run_ids=a,b`
- `GET /api/export/results.md?run_ids=a,b`
- `POST /api/shutdown`

## 文件说明

| 文件/目录 | 说明 |
|---|---|
| `serve_dashboard.py` | CLI 薄入口 |
| `dashboard/` | 后端模块化实现 |
| `monitor_dashboard.html` | 单文件前端，保留无构建工具模式 |
| `tests/` | pytest 测试与 fixtures |
| `docs/` | 架构、计划、协议和迁移说明 |

## 技术栈

- 后端：Python 3, FastAPI, Uvicorn
- 前端：原生 HTML + CSS + JavaScript, Chart.js
- 通信：Server-Sent Events
- 测试：pytest

## 开发

运行全部测试：

```bash
python -m pytest -v
```

## License

MIT
