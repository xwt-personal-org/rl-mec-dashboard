# Execution Report

## STATUS: NEEDS_REVIEW

> 上次更新：2026-05-06 | plan.md 版本：v3.3

## Last Execution

- 来源：dispatch:patch — plan v3.3 merge-back + 模块 13-14 Mainline-A 适配
- 摘要：完成 paper2 Mainline-A 新环境适配：新增 benchmark-only export discovery、BenchmarkSchemaAdapter、evidence boundary 展示、diagnostics API、前端 evidence badge/边界警告/结果表格列、compare evidence 混合检测、export evidence 列、删除目标扩展、启动脚本与文档更新。

## Completed

- [x] M13-S1：`dashboard/config.py` — paper2_root、CLI args、路径推导、helper 函数
- [x] M13-S2：`dashboard/models.py` + `dashboard/run_discovery.py` — SourceType 扩展、discover_benchmark_exports()、优先级去重
- [x] M13-S3：`dashboard/benchmark_schema.py`（新增）— BenchmarkSchemaAdapter、evidence 字段提取、raw_metrics 保留
- [x] M13-S4：`dashboard/state_aggregator.py` — scan_benchmark_export_once()、benchmark-only RunState 构建
- [x] M13-S5：`dashboard/api.py` — GET /api/mainline-a/diagnostics 端点
- [x] M13-S6：`start_dashboard.bat`、`README.md`、`docs/windows-start-menu-launcher.md` — 启动命令与文档更新
- [x] M13-S7：`tests/fixtures/mainline_a/` — 3 个 fixture 文件（18-item benchmark + 5-item benchmark + launch.json）
- [x] M13-S8：模块 13 回归测试通过
- [x] M14-S1：`dashboard/models.py` — RunSummary/RunState evidence 字段
- [x] M14-S2：`monitor_dashboard.html` — evidence badge、boundary warning、前端渲染函数
- [x] M14-S3：`api.py` + `exporter.py` — compare evidence 混合检测、CSV/MD export evidence 列
- [x] M14-S4：`monitor_dashboard.html` — 结果表格 Evidence/Scenario/CV Rate/Oracle Gap 列、raw_metrics toggle
- [x] M14-S5：`dashboard/delete_service.py` — benchmark_export 删除 target
- [x] M14-S6：`docs/mainline-a-dashboard-compatibility.md`（新增）— 兼容性文档
- [x] M14-S7：全量回归 — 158 passed，0 failures

## In Review

- [ ] 模块 13 Step 2-4,7-8 — benchmark discovery、schema adapter、RunState builder、fixtures、回归
- [ ] 模块 14 Step 2-3,5,7 — evidence 前端、compare 混合检测、删除扩展、最终回归

## Blocked

- 无

## Discovered Issues

- FastAPI `on_event` deprecated warning — 既有警告，严重度 low
- Plan v3.3 launch.json 假设名 "Benchmark Direct All 17" 与实际 "Mainline-A Full 17 Fresh" / "Direct Benchmark Dry Run" 不完全一致，已按实际名称适配

## Verification

- `python -m pytest -v`：158 passed，116 warnings，0 failures（22.88s）
- 所有既有测试（backup/archive/delete/convergence/config/models）通过
- 新增代码无 LSP 诊断错误

## Recommendations

- 启动 `start_dashboard.bat` 或使用 `--paper2-root` 命令行验证 `/api/mainline-a/diagnostics` 和 `/api/runs` 中 benchmark_direct_all_17_vscode 的展示
- paper2_full_17_vscode experiment_state 优先级已验证不被 direct export 覆盖

## Escalation Details

- 无
