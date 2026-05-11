# 开发计划：rl-mec-dashboard 适配 paper2 Mainline-A 新环境与 Full17 Benchmark

## 元信息

- 项目：`rl-mec-dashboard`
- 仓库：`w2030298-art/rl-mec-dashboard`
- 版本：v3.3
- 计划类型：已有项目迁移改造计划 — Iter merge-back
- 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。
- 当前架构基线：
  - 后端已模块化为 `dashboard/` 包。
  - 已支持 `paper2` 实验状态机、artifact 日志、benchmark export、backup/archive metadata、受控本地源文件删除。
  - 当前 dashboard 只读训练输出，不启动、不停止、不重启 paper2 训练。
- 本次变更来源：
  - paper2 已完成 Mainline-A 新环境搭建。
  - paper2 VSCode 调试机制已调整，使 Full17 benchmark 对比可运行在新环境上。
  - paper2 final review 已关闭为 `ACCEPTED_WITH_BOUNDARIES`；N0/N1/N2/N3 evidence level 不得被 dashboard 升级为更强结论。
  - rl-mec-dashboard 需要适配新环境输出、benchmark 直接运行结果、证据等级展示与启动配置。
- 总模块数：14
- 已完成模块：1-12
- 新增模块：13-14
- 历史完成步骤数：62
- 新增步骤数：15
- 预计总步骤数：77
- 当前待执行步骤数：15
- 建议开发顺序：模块 13 Step 1-8 → 模块 14 Step 1-7
- 创建日期：2026-04-28
- 最后更新：2026-05-06

### 变更记录

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v1 | 2026-04-28 | 初始完成 `rl-mec-dashboard` 对 `paper2` 新实验编排架构的迁移：实验状态、artifact 日志、benchmark export、API、前端、测试与文档。 |
| v2 | 2026-05-01 | 适配 `paper2` Patch 10 的 backup/archive 目录语义，避免 dashboard 将备份实验目录误识别为 active run，并新增只读备份归档展示能力。 |
| v3 | 2026-05-01 | 修复实际 VSCode backup 产物看板不可见问题，新增 backup 发现诊断与 archive-only 发现；新增受控本地源文件删除能力。 |
| v3.1 | 2026-05-02 | 根据用户反馈整理前端视觉层级与模块组织：监控主线前置，备份/算法/结果/日志/Danger Zone 分层展示。 |
| v3.2 | 2026-05-02 | 整理本地验证环境：关闭 8093 测试服务，恢复 8088 正式服务，补齐项目 venv 的 Playwright fallback。 |
| v3.3 | 2026-05-06 | 适配 paper2 Mainline-A 新环境与 VSCode Full17 benchmark：新增 benchmark-only discovery、Mainline-A schema adapter、evidence boundary 展示与启动配置校验。 |

---

## Status

> 任何 agent 读到此区块即可恢复完整上下文。

- 当前阶段：模块 13-14 完成，等待 review。
- 整体进度：77 / 77 步骤完成。
- 状态：NEEDS_REVIEW
- 阻塞项：无。
- 本次变更边界：
  - dashboard 仍是只读观察端。
  - 不新增训练启动、停止、恢复、重跑能力。
  - 不修改 paper2 训练代码。
  - 不把 `paper2/results/`、`experiments/`、`figures/`、`logs/` 纳入 Git tracking。
  - 不把 Mainline-A artifact-level evidence 渲染为正式 benchmark 结论。
  - Full17 benchmark 直接运行结果必须能在 dashboard 中作为可选数据源展示。

### Last Iteration Summary

模块 11 与模块 12 已完成，并按用户反馈补齐 backup 可作为 dashboard 选项展示、删除 target 覆盖 dashboard 已识别本地源文件、前端视觉与模块组织整理、本地验证环境整理。`/api/runs` 仍不混入 backup/archive，删除 API 仍只接受 discovery 产生的 `target_id`。

paper2 当前状态：Mainline-A final review 已关闭为 `ACCEPTED_WITH_BOUNDARIES`；N0 为 smoke evidence，N1 为 small-scale oracle evidence，N2 为 deterministic controlled probe only，N3 为 OOD formal execution evidence。dashboard 兼容性是 paper2 外部复核项。

### Pending Decisions

无。执行端按本 plan 执行；若发现 paper2 新输出 schema 无法从现有 tracked 文件推断，停在对应 `scope:review` 步骤并写入 `docs/report.md`。

---

## 关键设计原则

1. Dashboard 是只读观测层，不成为 paper2 训练编排器。
2. Mainline-A 新环境适配以“路径发现 + schema 兼容 + evidence 展示”为主，不接管 VSCode 调试。
3. `results/benchmark_direct_all_17_vscode.json` 等 benchmark-only 文件必须能独立成为 dashboard run source。
4. `experiments/<run_id>/state.json` 优先级仍高于 benchmark-only export。
5. backup/archive 与 benchmark-only export 都不得混入 active running list 的语义。
6. evidence level 必须显式展示，且 compare/chart 不得暗示正式 benchmark 结论。
7. 删除功能继续只接受后端 discovery 产生的 `target_id`，不得接受浏览器传入路径。
8. Windows 路径与 paper2 `.venv` 路径必须兼容。
9. 所有新增解析逻辑必须有 fixture 测试。
10. 所有 destructive endpoint 继续保留 preview + confirm token。
11. 启动脚本与 README 要明确新 paper2 root、results、experiments、figures、logs、benchmark direct export 的关系。

## 固定/新增 run id 与文件别名

```text
Full 17 run_id:              paper2_full_17_vscode
Quick run_id:                vscode_quick
Direct Full17 benchmark id:  benchmark_direct_all_17_vscode
Recommended direct output:   results/benchmark_direct_all_17_vscode.json
Standard export output:      results/benchmark_paper2_full_17_vscode.json
Global latest alias:         results/benchmark.json
```

---

# 历史模块状态

## 模块 1-9：paper2 新实验状态机适配 `[DONE]`

- **scope: auto**
- 当前状态：已完成。
- 步骤范围：Step 1-42。
- 本轮要求：不得重写；只允许因模块 13/14 测试需要做最小兼容修改。
- 验证：
  ```bash
  python -m pytest -v
  ```

## 模块 10：Patch 10 备份归档适配 `[DONE]`

- **scope: review**
- 当前状态：已完成。
- 步骤范围：Step 43-48。
- 本轮要求：保留 backup/archive 发现与 active run 排除语义；不要回滚。
- 验证：
  ```bash
  python -m pytest tests/test_run_discovery_experiments.py tests/test_api_experiments.py -v
  ```

## 模块 11：备份可见性修复与诊断增强 `[DONE]`

- **scope: review**
- 当前状态：已完成，等待人工 review。
- 步骤范围：Step 49-54。
- 保留要求：
  - `backup_scan_dirs` 与 `--backup-scan-dir` 继续可用。
  - `/api/backups/diagnostics` 继续显示 scanned roots、archive root、matched backups。
  - backup/archive 可以作为 dashboard option 展示。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_backup_static.py tests/test_api_experiments.py -v
  ```

## 模块 12：本地源文件删除功能 `[DONE]`

- **scope: review**
- 当前状态：已完成，等待人工 review。
- 步骤范围：Step 55-62。
- 保留要求：
  - 删除 API 只接受 `target_id`。
  - 删除 active run 前必须阻止 running / `process.json` 存在场景。
  - 删除 target 覆盖 active run、backup、archive-only、structured run、legacy log、benchmark export、global benchmark JSON。
- 验证：
  ```bash
  python -m pytest tests/test_delete_service.py tests/test_api_delete.py tests/test_frontend_delete_static.py -v
  ```

---

# 模块 13：Mainline-A 新环境与 Full17 benchmark 数据源适配

## 概述

- 职责：让 dashboard 识别 paper2 Mainline-A 新环境下的 VSCode Full17 benchmark 输出，尤其是 benchmark-only direct output。
- 前置依赖：模块 1-12。
- 预计步骤数：8
- 影响文件：
  - `dashboard/config.py`
  - `dashboard/models.py`
  - `dashboard/run_discovery.py`
  - `dashboard/state_aggregator.py`
  - `dashboard/api.py`
  - `dashboard/mainline_a.py`（新增）
  - `dashboard/benchmark_schema.py`（新增）
  - `monitor_dashboard.html`
  - `README.md`
  - `docs/windows-start-menu-launcher.md`
  - `tests/test_config.py`
  - `tests/test_mainline_a_discovery.py`（新增）
  - `tests/test_benchmark_schema.py`（新增）
  - `tests/test_api_experiments.py`
  - `tests/test_frontend_mainline_a_static.py`（新增）

## Step 1：新增 paper2 root 与 Mainline-A runtime 配置

- **scope: auto**
- 文件：`dashboard/config.py`
- 操作：
  1. 在 `DashboardConfig` 新增字段：
     ```python
     paper2_root: Path | None = None
     paper2_python: Path | None = None
     mainline_a_enabled: bool = True
     benchmark_scan_dirs: list[Path] = field(default_factory=list)
     benchmark_file_globs: list[str] = field(default_factory=lambda: ["benchmark*.json"])
     mainline_a_run_aliases: dict[str, str] = field(default_factory=dict)
     ```
  2. 修改 `parse_cli_args(argv)`，新增参数：
     ```bash
     --paper2-root C:/Users/22003/paper2/paper2
     --paper2-python C:/Users/22003/paper2/paper2/.venv/Scripts/python.exe
     --mainline-a-enabled true
     --benchmark-scan-dir C:/Users/22003/paper2/paper2/results
     --benchmark-file-glob benchmark*.json
     ```
  3. 新增 helper：
     ```python
     def paper2_runtime_roots(config: DashboardConfig) -> dict[str, Path | str | bool]:
         ...
     ```
  4. 新增 helper：
     ```python
     def benchmark_scan_roots(config: DashboardConfig) -> list[Path]:
         ...
     ```
- 实现规则：
  - `paper2_root` 存在时，默认推导：
    - `experiments_dir = paper2_root / "experiments"`，仅当 CLI 未显式指定时生效。
    - `results_dir = paper2_root / "results"`，仅当 CLI 未显式指定时生效。
    - `figures_dir = paper2_root / "figures"`，仅当 CLI 未显式指定时生效。
    - `logs_dir = paper2_root / "logs"`，仅当 CLI 未显式指定时生效。
    - `benchmark_scan_dirs` 默认包含 `results_dir`。
  - 不在配置解析阶段要求路径存在；存在性由 diagnostics 报告。
  - `mainline_a_run_aliases` 默认至少包含：
    ```python
    {
        "benchmark_direct_all_17_vscode": "Direct Full17 Benchmark",
        "paper2_full_17_vscode": "Paper2 Full17 Experiment",
        "vscode_quick": "VSCode Quick Benchmark",
    }
    ```
- 验证：
  ```bash
  python -m pytest tests/test_config.py::test_paper2_root_derives_default_dirs -v
  python -m pytest tests/test_config.py::test_benchmark_scan_dir_can_be_repeated_and_deduped -v
  python -m pytest tests/test_config.py::test_mainline_a_alias_defaults_are_present -v
  ```

## Step 2：新增 benchmark-only export discovery

- **scope: review**
- 文件：
  - `dashboard/models.py`
  - `dashboard/run_discovery.py`
- 操作：
  1. 在 `SourceType` 增加：
     ```python
     "benchmark_export"
     "mainline_a_benchmark"
     ```
  2. 在 `RunDescriptor` 增加字段：
     ```python
     benchmark_only: bool = False
     benchmark_label: str = ""
     benchmark_stage: str = ""
     evidence_level: str = ""
     ```
  3. 新增函数：
     ```python
     def discover_benchmark_exports(results_dir: Path, scan_dirs: list[Path], globs: list[str]) -> list[RunDescriptor]:
         ...
     ```
  4. 修改 `discover_runs(config)`：
     - 保持 experiment_state 优先。
     - structured / legacy 逻辑不变。
     - 在 placeholders 前追加 benchmark-only exports。
- 发现规则：
  - 扫描 `config.results_dir` 与 `config.benchmark_scan_dirs`。
  - 匹配 `benchmark*.json`。
  - 必须排除临时文件：`*.tmp`、`*.bak`、`*.err`。
  - `benchmark_paper2_full_17_vscode.json` 映射为 run id `paper2_full_17_vscode`。
  - `benchmark_direct_all_17_vscode.json` 映射为 run id `benchmark_direct_all_17_vscode`。
  - `benchmark.json` 映射为 `benchmark_json_latest`，但若已有更具体的 `benchmark_<run_id>.json`，不覆盖。
  - 若 JSON 内存在 Mainline-A evidence 字段，`source_type = "mainline_a_benchmark"`；否则 `source_type = "benchmark_export"`。
- 去重规则：
  - 同一 run_id 优先级：
    1. `experiment_state`
    2. `mainline_a_benchmark`
    3. `benchmark_export`
    4. `legacy_structured`
    5. `legacy_log`
    6. `placeholder`
  - 同一物理文件只生成一个 descriptor。
- 验证：
  ```bash
  python -m pytest tests/test_mainline_a_discovery.py::test_discover_direct_full17_benchmark_export -v
  python -m pytest tests/test_mainline_a_discovery.py::test_experiment_state_wins_over_benchmark_only_export -v
  python -m pytest tests/test_mainline_a_discovery.py::test_global_benchmark_json_does_not_hide_specific_export -v
  ```

## Step 3：新增 Mainline-A benchmark schema adapter

- **scope: review**
- 文件：
  - `dashboard/benchmark_schema.py`（新增）
  - `dashboard/run_discovery.py`
  - `dashboard/models.py`
- 操作：
  1. 新增类：
     ```python
     class BenchmarkSchemaAdapter:
         def normalize_item(self, item: dict[str, Any], source_path: Path | None = None) -> AlgorithmResult:
             ...
         def detect_schema(self, payload: Any) -> str:
             ...
         def extract_run_metadata(self, payload: Any, source_path: Path) -> dict[str, Any]:
             ...
     ```
  2. 修改 `load_benchmark_results(json_path)`，内部委托 `BenchmarkSchemaAdapter.normalize_item()`。
  3. 在 `AlgorithmResult` 新增字段：
     ```python
     scenario: str = ""
     stage: str = ""
     evidence_level: str = ""
     boundary_note: str = ""
     composite_score: float | None = None
     oracle_gap: float | None = None
     deadline_violation_rate: float | None = None
     constraint_violation_rate: float | None = None
     raw_metrics: dict[str, Any] = field(default_factory=dict)
     ```
- 兼容字段：
  - 既有字段：
    - `algorithm`
    - `final_reward_mean`
    - `final_reward_std`
    - `final_latency_mean`
    - `final_energy_mean`
    - `final_deadline_miss_rate_mean`
    - `final_throughput_tasks_per_step_mean`
    - `final_comm_score`
    - `train_time_seconds_mean`
    - `total_updates_mean`
  - Mainline-A 字段候选：
    - `stage`
    - `scenario`
    - `evidence_level`
    - `boundary_note`
    - `oracle_gap`
    - `constraint_violation_rate`
    - `deadline_violation_rate`
    - `composite_score`
    - `environment`
    - `train_timesteps`
    - `device`
    - `seed`
    - `status`
  - 不能识别的字段进入 `raw_metrics`，不得丢弃。
- evidence 默认规则：
  - 文件名或内容包含 `n0` → `smoke evidence`
  - 文件名或内容包含 `n1` → `small-scale oracle evidence`
  - 文件名或内容包含 `n2` → `deterministic controlled probe only`
  - 文件名或内容包含 `n3` 或 `ood` → `OOD formal execution evidence`
  - `benchmark_direct_all_17_vscode.json` 若无 evidence 字段 → `benchmark evidence pending review`
- 验证：
  ```bash
  python -m pytest tests/test_benchmark_schema.py::test_adapter_preserves_legacy_benchmark_fields -v
  python -m pytest tests/test_benchmark_schema.py::test_adapter_normalizes_mainline_a_evidence_fields -v
  python -m pytest tests/test_benchmark_schema.py::test_adapter_keeps_unknown_metrics_in_raw_metrics -v
  python -m pytest tests/test_benchmark_schema.py::test_direct_full17_without_evidence_gets_pending_review_boundary -v
  ```

## Step 4：让 benchmark-only export 可构建完整 RunState

- **scope: review**
- 文件：
  - `dashboard/state_aggregator.py`
  - `dashboard/run_discovery.py`
  - `dashboard/api.py`
- 操作：
  1. 在 `RunStateAggregator.initialize_state(descriptor)` 支持：
     ```python
     descriptor.source_type in {"benchmark_export", "mainline_a_benchmark"}
     ```
  2. 新增方法：
     ```python
     def scan_benchmark_export_once(self, descriptor: RunDescriptor, state: RunState) -> RunState:
         ...
     ```
  3. 修改 `DashboardStateStore.scan_all_once()` 或对应扫描路径：
     - 当 descriptor 为 benchmark-only 时，不尝试读取 `state.json`。
     - 直接从 `benchmark_export_file` 构建 `results`、`completed_algorithms`、`total_algorithms`、`progress_pct=100.0`。
  4. 修改 `/api/runs/{run_id}/benchmark`：
     - 对 benchmark-only run 返回其物理文件。
     - 对 experiment_state run 仍优先返回 `results/benchmark_<run_id>.json`。
- 状态规则：
  - benchmark-only export 的 `status = "finished"`。
  - `current_algorithm = ""`。
  - `process_alive = False`。
  - `possibly_stale = False`，除非 JSON 读取失败。
  - `degraded = True` 仅在 schema adapter 报出 parse warnings 时。
- 验证：
  ```bash
  python -m pytest tests/test_mainline_a_discovery.py::test_benchmark_only_export_builds_finished_run_state -v
  python -m pytest tests/test_api_experiments.py::test_api_runs_includes_direct_full17_benchmark_source -v
  python -m pytest tests/test_api_experiments.py::test_get_run_benchmark_uses_direct_export_path -v
  ```

## Step 5：新增 Mainline-A diagnostics API

- **scope: auto**
- 文件：`dashboard/api.py`
- 操作：新增 endpoint：
  ```python
  @app.get("/api/mainline-a/diagnostics")
  async def mainline_a_diagnostics():
      ...
  ```
- 返回结构：
  ```json
  {
    "paper2_root": "...",
    "paper2_python": "...",
    "mainline_a_enabled": true,
    "experiments_dir": "...",
    "results_dir": "...",
    "figures_dir": "...",
    "logs_dir": "...",
    "benchmark_scan_dirs": ["..."],
    "benchmark_files": [
      {"path": ".../benchmark_direct_all_17_vscode.json", "exists": true, "schema": "mainline_a", "algorithms": 17}
    ],
    "launch_json": {"path": ".../.vscode/launch.json", "exists": true, "has_direct_full17": true},
    "notes": []
  }
  ```
- 规则：
  - 不读取大文件全文；JSON payload 只读取必要元数据。
  - `.vscode/launch.json` 存在时检查是否包含 `"Benchmark Direct All 17"` 或 `benchmark_direct_all_17_vscode.json`。
  - 不抛 500；异常写入 `notes`。
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_mainline_a_diagnostics_reports_direct_full17_export -v
  python -m pytest tests/test_api_experiments.py::test_mainline_a_diagnostics_handles_missing_launch_json -v
  ```

## Step 6：更新 Windows 启动入口与 README

- **scope: auto**
- 文件：
  - `README.md`
  - `docs/windows-start-menu-launcher.md`
  - `start_dashboard.bat`
  - `start_dashboard.vbs`（仅当需传参变更）
- 操作：
  1. README 新增 Mainline-A 推荐启动命令：
     ```powershell
     C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py ^
       --paper2-root C:\Users\22003\paper2\paper2 ^
       --paper2-python C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe ^
       --experiments-dir C:\Users\22003\paper2\paper2\experiments ^
       --results-dir C:\Users\22003\paper2\paper2\results ^
       --figures-dir C:\Users\22003\paper2\paper2\figures ^
       --logs-dir C:\Users\22003\paper2\paper2\logs ^
       --benchmark-scan-dir C:\Users\22003\paper2\paper2\results ^
       --backup-scan-dir C:\Users\22003\paper2\paper2\experiments ^
       --host 127.0.0.1 --port 8088
     ```
  2. 文档明确：
     - `Benchmark Direct All 17` 输出为 benchmark-only 数据源。
     - dashboard 不启动 VSCode debug config。
     - `ACCEPTED_WITH_BOUNDARIES` 只作为 evidence boundary 显示。
  3. `start_dashboard.bat` 默认传入 `--paper2-root`，但允许环境变量覆盖：
     ```bat
     set PAPER2_ROOT=C:\Users\22003\paper2\paper2
     set PAPER2_PYTHON=%PAPER2_ROOT%\.venv\Scripts\python.exe
     ```
- 验证：
  ```bash
  python -m pytest tests/test_frontend_mainline_a_static.py::test_docs_reference_mainline_a_startup_flags -v
  ```

## Step 7：补齐 paper2 v4.2 / Mainline-A fixtures

- **scope: review**
- 文件：
  - `tests/fixtures/mainline_a/results/benchmark_direct_all_17_vscode.json`
  - `tests/fixtures/mainline_a/results/benchmark_paper2_full_17_vscode.json`
  - `tests/fixtures/mainline_a/.vscode/launch.json`
  - `tests/test_mainline_a_discovery.py`
  - `tests/test_benchmark_schema.py`
- fixture 要求：
  - 至少覆盖 17 个算法名。
  - 至少包含一个 legacy-style result item。
  - 至少包含一个 Mainline-A item，含 `evidence_level`。
  - 至少包含一个未知 metric 字段，用于验证 `raw_metrics`。
  - `launch.json` 包含 `Benchmark Direct All 17` 与 `results/benchmark_direct_all_17_vscode.json`。
- 验证：
  ```bash
  python -m pytest tests/test_mainline_a_discovery.py tests/test_benchmark_schema.py -v
  ```

## Step 8：模块 13 回归与报告更新

- **scope: review**
- 文件：
  - `docs/progress.md`
  - `docs/report.md`
  - `docs/issues.md`
- 操作：
  - 更新 `docs/progress.md` 模块 13 完成状态。
  - 更新 `docs/report.md`：
    - `STATUS: CHANGE_IN_PROGRESS` 或 `NEEDS_REVIEW`。
    - 记录 Mainline-A diagnostics 输出摘要。
    - 记录 direct Full17 export 是否被 `/api/runs` 识别。
  - 若发现无法解析的 Mainline-A 字段，追加 `docs/issues.md`：
    ```markdown
    - [Open] Mainline-A-schema-unknown-field: <字段名> — <文件路径>
    ```
- 验证：
  ```bash
  python -m pytest tests/test_config.py tests/test_mainline_a_discovery.py tests/test_benchmark_schema.py tests/test_api_experiments.py -v
  python -m pytest -v
  ```

## 模块 13 验收标准

- [ ] 使用 `--paper2-root` 可推导 paper2 experiments/results/figures/logs 默认路径。
- [ ] `/api/mainline-a/diagnostics` 能报告 `.vscode/launch.json` 与 direct Full17 benchmark export。
- [ ] `results/benchmark_direct_all_17_vscode.json` 可作为独立 run 出现在 `/api/runs`。
- [ ] benchmark-only run 可进入详情页，显示结果图表。
- [ ] 现有 `paper2_full_17_vscode` experiment_state 优先级不被 direct export 覆盖。
- [ ] 原有 backup/archive/delete 测试不退化。

---

# 模块 14：Mainline-A evidence boundary 与前端展示适配

## 概述

- 职责：把 paper2 final review 的 evidence boundary 作为 dashboard 一等展示信息，避免把 N0/N1/N2/N3 或 Direct Full17 artifact 输出误读为正式 benchmark 结论。
- 前置依赖：模块 13。
- 预计步骤数：7
- 影响文件：
  - `dashboard/models.py`
  - `dashboard/api.py`
  - `dashboard/exporter.py`
  - `monitor_dashboard.html`
  - `tests/test_api_experiments.py`
  - `tests/test_exporter.py`
  - `tests/test_frontend_mainline_a_static.py`
  - `README.md`
  - `docs/progress.md`
  - `docs/report.md`

## Step 1：扩展 API DTO 的 evidence boundary 字段

- **scope: auto**
- 文件：
  - `dashboard/models.py`
  - `dashboard/api.py`
- 操作：
  1. 在 `RunSummary` 新增：
     ```python
     evidence_level: str = ""
     evidence_boundary: str = ""
     ```
  2. 在 `RunState` 新增：
     ```python
     evidence_level: str = ""
     evidence_boundary: str = ""
     benchmark_schema: str = ""
     ```
  3. `run_summary_to_dict()` 与 `run_state_to_dict()` 不做字段过滤，沿用 `dataclass_to_dict()`。
  4. `RunStateAggregator` 对 `mainline_a_benchmark` descriptor 填充：
     ```text
     evidence_level = descriptor.evidence_level or "benchmark evidence pending review"
     evidence_boundary = "Do not promote artifact-level evidence into stronger formal benchmark conclusions."
     benchmark_schema = "mainline_a"
     ```
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_run_summary_exposes_evidence_boundary -v
  python -m pytest tests/test_api_experiments.py::test_run_state_exposes_benchmark_schema -v
  ```

## Step 2：前端新增 evidence badge 与 boundary warning

- **scope: review**
- 文件：`monitor_dashboard.html`
- 操作：
  1. 新增函数：
     ```js
     function renderEvidenceBadge(evidenceLevel) { ... }
     function renderEvidenceBoundary(state) { ... }
     function evidenceLevelClass(evidenceLevel) { ... }
     ```
  2. 在 run selector 每个 option/row 增加 evidence 标签：
     - `smoke evidence`
     - `small-scale oracle evidence`
     - `deterministic controlled probe only`
     - `OOD formal execution evidence`
     - `benchmark evidence pending review`
  3. 在详情区核心指标上方增加 warning：
     ```text
     Evidence boundary: do not promote artifact-level evidence into stronger formal benchmark conclusions.
     ```
  4. 对 `benchmark_direct_all_17_vscode` 默认显示：
     ```text
     Direct Full17 benchmark export; review boundary required before interpreting as formal conclusion.
     ```
- 禁止：
  - 不使用 “paper conclusion” / “publication-grade” 等文案。
  - 不把 N2 显示为 ablation conclusion。
  - 不把 Direct Full17 显示为 accepted final benchmark，除非数据中明确 evidence 字段。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_mainline_a_static.py::test_frontend_contains_evidence_badges -v
  python -m pytest tests/test_frontend_mainline_a_static.py::test_frontend_warns_direct_full17_pending_review -v
  ```

## Step 3：compare/chart 避免跨 evidence level 误导

- **scope: review**
- 文件：
  - `dashboard/api.py`
  - `dashboard/exporter.py`
  - `monitor_dashboard.html`
- 操作：
  1. 修改 `/api/compare` 返回结构，增加：
     ```json
     {
       "evidence_mixed": true,
       "evidence_levels": ["smoke evidence", "benchmark evidence pending review"],
       "warning": "Compared runs have different evidence levels."
     }
     ```
  2. 前端 compare 区显示 warning。
  3. CSV/Markdown export 增加列：
     - `evidence_level`
     - `evidence_boundary`
     - `benchmark_schema`
  4. 如果 compare 中混合了 `deterministic controlled probe only` 与 direct benchmark，则 warning 必须显示。
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_compare_reports_mixed_evidence_levels -v
  python -m pytest tests/test_exporter.py::test_export_includes_evidence_columns -v
  python -m pytest tests/test_frontend_mainline_a_static.py::test_frontend_compare_displays_evidence_warning -v
  ```

## Step 4：更新结果表格与算法详情字段

- **scope: auto**
- 文件：`monitor_dashboard.html`
- 操作：
  1. Results table 新增列：
     - `Evidence`
     - `Scenario`
     - `Constraint Violation`
     - `Oracle Gap`
  2. 字段为空时显示 `—`。
  3. `raw_metrics` 不直接全量展示，避免页面噪声；只在 expandable detail 中显示前 20 个 key。
  4. 对 `constraint_violation_rate > 0` 的算法结果增加非破坏性提示。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_mainline_a_static.py::test_results_table_contains_mainline_a_columns -v
  ```

## Step 5：让删除目标覆盖新 benchmark-only exports

- **scope: review**
- 文件：
  - `dashboard/delete_service.py`
  - `tests/test_delete_service.py`
  - `tests/test_api_delete.py`
- 操作：
  1. `LocalDataDeleteService.list_targets()` 纳入 `discover_benchmark_exports()` 结果。
  2. 新增 target_id：
     ```text
     benchmark_export:benchmark_direct_all_17_vscode
     benchmark_export:benchmark_json_latest
     ```
  3. 删除 preview 显示实际 benchmark JSON 文件路径。
  4. 删除 confirm 后刷新 `/api/runs` 与 `/api/mainline-a/diagnostics`。
- 安全规则：
  - 仍只允许删除白名单根目录内文件。
  - 不允许删除 `results/` 根目录。
  - 不允许通过 target_id 删除 archive 目录之外的父目录。
- 验证：
  ```bash
  python -m pytest tests/test_delete_service.py::test_list_targets_includes_direct_full17_benchmark_export -v
  python -m pytest tests/test_api_delete.py::test_delete_confirm_removes_direct_benchmark_export_and_refreshes -v
  ```

## Step 6：文档更新：Mainline-A dashboard 使用边界

- **scope: auto**
- 文件：
  - `README.md`
  - `docs/windows-start-menu-launcher.md`
  - `docs/mainline-a-dashboard-compatibility.md`（新增）
- 操作：
  1. 新增 `docs/mainline-a-dashboard-compatibility.md`，包含：
     - 启动命令。
     - 数据源优先级。
     - direct benchmark-only export 语义。
     - evidence boundary 解释。
     - `/api/mainline-a/diagnostics` 使用方式。
     - 删除 target 的安全边界。
  2. README 增加链接。
  3. Windows launcher 文档说明如何覆盖 `PAPER2_ROOT`。
- 验证：
  ```bash
  test -f docs/mainline-a-dashboard-compatibility.md
  grep -n "benchmark_direct_all_17_vscode" docs/mainline-a-dashboard-compatibility.md
  grep -n "evidence boundary" docs/mainline-a-dashboard-compatibility.md
  ```

## Step 7：全量回归与 v3.3 状态收口

- **scope: review**
- 文件：
  - `docs/plan.md`
  - `docs/progress.md`
  - `docs/report.md`
  - `docs/issues.md`
- 操作：
  1. 更新 `docs/plan.md` Status：
     - 当前阶段：模块 13-14 完成，等待 review。
     - 整体进度：77 / 77。
     - 状态：NEEDS_REVIEW。
  2. 更新 `docs/progress.md`：
     - 模块 13 Step 1-8 完成。
     - 模块 14 Step 1-7 完成。
  3. 更新 `docs/report.md`：
     - `STATUS: NEEDS_REVIEW`
     - 记录 Mainline-A diagnostics、direct Full17 export discovery、mixed evidence compare warning 验证结果。
  4. 若测试失败，保留 `CHANGE_IN_PROGRESS` 并写入 `Blocked`。
- 全量验证：
  ```bash
  python -m pytest tests/test_config.py tests/test_mainline_a_discovery.py tests/test_benchmark_schema.py tests/test_api_experiments.py tests/test_delete_service.py tests/test_api_delete.py -v
  python -m pytest tests/test_frontend_backup_static.py tests/test_frontend_delete_static.py tests/test_frontend_mainline_a_static.py -v
  python -m pytest -v
  ```
- 手动验证：
  ```bash
  python serve_dashboard.py ^
    --paper2-root C:\Users\22003\paper2\paper2 ^
    --paper2-python C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe ^
    --host 127.0.0.1 --port 8088
  ```
  浏览器检查：
  - `http://127.0.0.1:8088/api/health`
  - `http://127.0.0.1:8088/api/mainline-a/diagnostics`
  - `http://127.0.0.1:8088/api/runs`
  - 页面 run selector 是否出现 `benchmark_direct_all_17_vscode`
  - Direct Full17 详情页是否显示 evidence warning

## 模块 14 验收标准

- [ ] `/api/runs` 与 `/api/runs/{run_id}` 输出 evidence fields。
- [ ] 前端 run selector、详情页、compare 区显示 evidence boundary。
- [ ] compare 混合不同 evidence level 时显示 warning。
- [ ] export CSV/Markdown 包含 evidence 列。
- [ ] Direct Full17 benchmark-only export 可删除，但仍通过 preview + confirm token。
- [ ] README 与新增兼容文档说明 Mainline-A dashboard 使用边界。
- [ ] 全量 pytest 通过。

---

# v3.3 总体验收标准

- [ ] dashboard 能在 paper2 Mainline-A 新环境下通过 `--paper2-root` 启动。
- [ ] VSCode `Benchmark Direct All 17` 的输出文件可被 dashboard 自动发现。
- [ ] `paper2_full_17_vscode` active experiment 与 `benchmark_direct_all_17_vscode` direct export 不互相覆盖。
- [ ] benchmark-only export 可以作为 run 进入详情、图表、导出与删除 target。
- [ ] Mainline-A benchmark schema 的未知字段不丢失，进入 `raw_metrics`。
- [ ] evidence boundary 在 API、前端、compare、export 中一致。
- [ ] 旧 backup/archive/delete 能力不退化。
- [ ] dashboard 仍不启动、不停止、不恢复 paper2 训练。
- [ ] 所有新增步骤都有 fixture 测试与全量回归。

---

# 执行纪律

- `scope:auto` 内执行端可自主迭代，验证通过直接进入下一步。
- `scope:review` 完成后必须在 `docs/report.md` 记录验证结果与风险点，但不需要停下等待，除非出现 schema 无法判断或破坏性行为。
- 不新增训练控制 API。
- 不把 generated artifacts 纳入 Git tracking。
- 不删除用户本地结果，除非用户在 dashboard Danger Zone 中完成 preview + exact confirm。
- 若发现 paper2 新 benchmark schema 与本 plan 假设冲突，标记 `NEEDS_ESCALATION`，并在 `docs/report.md` 写明冲突字段与样例路径。
