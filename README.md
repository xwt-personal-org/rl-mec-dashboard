# RL-MEC Training Dashboard

轻量级网页看板，用于实时监控 RL-MEC Benchmark 训练任务状态。Dashboard 只读训练输出文件，不启动、不停止、不重启 paper2 训练任务。

## 功能

- 实时状态监控：优先读取 `experiments/<run_id>/state.json`，展示当前算法、状态、日志和结果。
- 多运行总览：固定显示 Full 17 与 Quick 入口，并兼容 legacy logs、structured runs 和 mixed runs。
- paper2 实验协议优先：优先读取 `experiments/<run_id>/run.json`、`state.json` 和每算法 artifacts。
- Legacy fallback：没有 paper2 experiments 时继续读取旧 `runs/`、`logs/benchmark*.log` 和 `results/benchmark.json`。
- 多实验对比：`/api/compare` 支持按 reward、latency、energy 等指标对比。
- 结果导出：支持 CSV 和 Markdown 表格导出。
- SSE 实时推送：前端通过 Server-Sent Events 刷新 run snapshot。
- Stop Dashboard Server：只关闭 dashboard server，不停止训练任务。

## 启动方式

### Windows 菜单栏一键启动（推荐）

首次安装快捷方式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
```

安装后从 Windows 开始菜单启动：

```text
Start / 开始菜单 → RL-MEC Dashboard → RL-MEC Dashboard
```

该入口会静默调用 `start_dashboard.vbs`，再由 `start_dashboard.bat --hidden` 启动 dashboard server 并打开浏览器。

卸载开始菜单快捷方式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
```

说明：此入口只启动 dashboard server，不启动、不停止、不重启 paper2 训练任务。

### 命令行

推荐 paper2 experiments 模式：

```bash
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --experiments-dir C:\Users\22003\paper2\paper2\experiments \
    --results-dir C:\Users\22003\paper2\paper2\results \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --host 127.0.0.1 --port 8088
```

Legacy fallback 仍可显式传入旧路径：

```bash
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --experiments-dir C:\Users\22003\paper2\paper2\experiments \
    --results-dir C:\Users\22003\paper2\paper2\results \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json \
    --runs-dir C:\Users\22003\paper2\paper2\runs \
    --host 127.0.0.1 --port 8088
```

访问：`http://127.0.0.1:8088`

### Windows 启动脚本

- `start_dashboard.vbs`：静默启动并打开浏览器。
- `start_dashboard.bat`：可见控制台启动，便于查看 server 输出。

`start_dashboard.vbs` / `start_dashboard.bat` 仍作为底层兼容入口保留；普通使用优先从 Windows 开始菜单启动。

页面上的 `Stop Dashboard Server` 只关闭 dashboard server；它不停止训练、不清理训练进程、不修改 paper2 输出。

固定入口：

- Full 17 run id：`paper2_full_17_vscode`
- Quick run id：`vscode_quick`
- Quick smoke test 只用于入口连通性和失败定位，不作为正式论文结果。

## 数据源优先级

1. paper2 实时状态：`experiments/<run_id>/run.json` + `experiments/<run_id>/state.json`
2. 每算法结果：`experiments/<run_id>/artifacts/<ALGORITHM>/result.json`
3. benchmark 图表导出：`results/benchmark_<run_id>.json`
4. legacy fallback：旧 `runs/`、`logs/`、`results/benchmark.json`

详见：

- `docs/paper2-experiment-architecture-sync.md`

## API

- `GET /api/health`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `GET /api/runs/{run_id}/logs/{algorithm}/stdout`
- `GET /api/runs/{run_id}/logs/{algorithm}/stderr`
- `GET /api/runs/{run_id}/benchmark`
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
