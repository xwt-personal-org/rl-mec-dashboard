# RL-MEC Training Dashboard — AGENTS.md

## Project Overview

Lightweight web dashboard for monitoring RL-MEC benchmark training runs in real-time.
Target project: `C:\Users\22003\paper2\paper2`
This project: `C:\Users\22003\paper2\web_dashboard`

## Key Files

- `serve_dashboard.py` — CLI 薄入口，调用 `dashboard/` 包
- `dashboard/` — 后端模块化实现
  - `api.py` — FastAPI 路由定义
  - `state_aggregator.py` — 状态聚合与判定逻辑
  - `log_parser.py` — 日志解析
  - `config.py` — 配置与 CLI 参数
  - `models.py` — 数据模型
  - `exporter.py` — CSV/Markdown 导出
  - `sse.py` — Server-Sent Events
  - `run_discovery.py` — Run 发现与加载
  - `experiment_reader.py` — 实验目录读取
  - `protocol_reader.py` — 结构化协议读取
  - `convergence.py` — 收敛曲线加载
  - `delete_service.py` — 删除服务
- `monitor_dashboard.html` — Standalone frontend (no build step)
- `start_dashboard.bat` / `start_dashboard.vbs` — Launch scripts (vbs hides console window)

## Launch Commands

```bash
# Via vbs (no console window, auto-opens browser)
start_dashboard.vbs

# Or via bat directly
start_dashboard.bat

# Or manual
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json \
    --port 8088
```

Dashboard URL: `http://127.0.0.1:8088`

## Dependencies

`fastapi`, `uvicorn` — installed in `paper2\.venv`. Do NOT use system Python.
The bat file already uses the venv Python path. If running manually, use the venv Python.

## Log Parsing (Critical)

Two benchmark.py log formats exist:

**Old format** (pre-2026-04-24): separate `benchmark_*.log` (stdout) + `benchmark_*.err.log` (stderr with tqdm progress)
**New format** (2026-04-24+): single `benchmark_*.log` with `INFO - ` prefix on every line

All parsing functions use `strip_log_prefix()` first — every regex operates on the stripped content.

Key patterns:
- Algorithm switch: `Algorithm:\s*(\w+)` (stripped line)
- Result: `\[(\w+)\]\s+reward=([-\d.]+)\+/-([-\d.]+)\s+time=([\d.]+)s`
- Progress: `Training\s+(\w+Agent):\s+\d+%\|[^|]*\|\s+(\d+)/(\d+)\s+\[[^]]*,\s+([\d.]+)it/s`
- ETA: `<H:MM:SS` or `<MM:SS` or `<SS>s` after `strip_log_prefix`

## Data Sources

- **log_results**: Parsed from current run's `.log` file — drives progress and charts
- **historical_results**: Loaded from `benchmark.json` — only fills in algorithms NOT in log_results (backfills latency/energy, greyed as "historical")
- **overall_progress**: `completed_algorithms count + current_algorithm_fraction` — only counts log-sourced completions

## API Endpoints

- `GET /api/runs` — discover all runs in log directory
- `GET /api/runs/{run_id}` — snapshot of a run
- `GET /api/runs/{run_id}/events` — SSE stream (1 snapshot/sec)
- `GET /api/runs/{run_id}/logs/{algorithm}/stdout` — algorithm stdout log tail
- `GET /api/runs/{run_id}/logs/{algorithm}/stderr` — algorithm stderr log tail
- `GET /api/runs/{run_id}/convergence` — convergence curve data
- `GET /api/runs/{run_id}/benchmark` — benchmark export data
- `GET /api/compare` — multi-run comparison
- `GET /api/export/results.csv` — CSV export
- `GET /api/export/results.md` — Markdown export
- `GET /api/backups` — list all backups
- `GET /api/backups/{backup_id}` — backup detail
- `GET /api/backups/diagnostics` — backup scan diagnostics
- `POST /api/delete-preview` — preview delete targets
- `POST /api/delete-confirm` — confirm deletion
- `POST /api/shutdown` — shutdown dashboard server
- `GET /` — serves `monitor_dashboard.html`

## Common Mistakes to Avoid

1. **Using system Python** instead of `paper2\.venv\Scripts\python.exe` — fastapi/uvicorn not in system Python
2. **Modifying parse regexes without `strip_log_prefix()`** — new format lines all have `INFO - ` prefix
3. **Adding benchmark.json completions to `completed_algorithms`** — only log-parsed results count for progress
4. **Assuming `discover_runs()` always finds `.err.log`** — new format has none; falls back to using `.log` for both streams
5. **`scan_log_file()` no longer distinguishes stderr/stdout** — both streams are merged in single file now

## Architecture Notes

- 模块化后端 (`dashboard/` 包)，单 HTML 文件前端
- In-memory state only (no database)
- Background scan thread updates all RunState every 1 second
- `load_benchmark_json()` called on every scan cycle to backfill missing latency/energy
- `_merge_results()` sorts by train_time for display, not by reward
