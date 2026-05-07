# Mainline-A Dashboard Compatibility

## 概述

本文档说明 rl-mec-dashboard 在 paper2 Mainline-A 新环境下的使用方式、数据源优先级和 evidence boundary 机制。

## 启动命令

```powershell
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py `
  --paper2-root C:\Users\22003\paper2\paper2 `
  --paper2-python C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe `
  --host 127.0.0.1 --port 8088
```

## 数据源优先级

Dashboard 按以下优先级发现和展示 run：

1. **experiment_state** — paper2 实验目录中的 active experiment
2. **mainline_a_benchmark** — 包含 Mainline-A evidence 字段的 benchmark-only export
3. **benchmark_export** — 标准 benchmark JSON export（无 evidence 字段）
4. **legacy_structured** — 旧版 structured run 目录
5. **legacy_log** — 旧版日志文件
6. **placeholder** — 固定入口（Full 17、Quick）

同一 run_id 按上述优先级去重。

## Benchmark-Only Export

- `results/benchmark_direct_all_17_vscode.json` 作为独立 benchmark-only 数据源展示
- Dashboard 不启动 VSCode debug config，仅供已有输出文件的只读观测
- Benchmark-only export 的 RunState 状态为 `finished`，progress 为 100%

## Evidence Boundary

paper2 final review 关闭为 `ACCEPTED_WITH_BOUNDARIES`。Dashboard 中的 evidence level 按以下分类展示：

| Evidence Level | 含义 | 来源 |
|---|---|---|
| smoke evidence | N0 快速验证 | 文件名/内容含 n0 |
| small-scale oracle evidence | N1 小规模 oracle | 文件名/内容含 n1 |
| deterministic controlled probe only | N2 受控探针 | 文件名/内容含 n2 |
| OOD formal execution evidence | N3 OOD 形式化执行 | 文件名/内容含 n3 或 ood |
| benchmark evidence pending review | 待审核 | Direct Full17 无 evidence 字段 |

**重要**：Dashboard 不升级任何 evidence level。`ACCEPTED_WITH_BOUNDARIES` 仅作为 boundary 说明展示。

## Diagnostics API

`GET /api/mainline-a/diagnostics` 返回：
- paper2 runtime roots
- benchmark 文件扫描（schema 类型、算法数量）
- `.vscode/launch.json` 状态

## 删除安全边界

- 删除 API 仍只接受 `target_id`，不接受浏览器传入路径
- 新增 `benchmark_export:<run_id>` 类型的删除 target
- 删除 preview 显示实际文件路径
- 删除 confirm 后刷新 `/api/runs` 和 `/api/mainline-a/diagnostics`

## 环境变量

`start_dashboard.bat` 默认使用硬编码路径。可通过环境变量覆盖：

```bat
set PAPER2_ROOT=D:\my-projects\paper2
start_dashboard.bat
```
