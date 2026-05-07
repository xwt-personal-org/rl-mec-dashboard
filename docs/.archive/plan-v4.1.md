# 开发计划：rl-mec-dashboard 算法收敛性能曲线展示

## 元信息

- 项目：`rl-mec-dashboard`
- 仓库：`w2030298-art/rl-mec-dashboard`
- 版本：v4.1
- 计划类型：已有项目迁移改造计划 — Iter merge-back
- 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。
- 当前架构基线：后端已模块化为 `dashboard/` 包，已支持 `paper2` 实验状态机、artifact 日志、benchmark export、backup/archive metadata 展示、受控删除本地源文件。
- 本次变更来源：`paper2` 已新增 benchmark 收敛数据与 `convergence_curves` 绘图能力。
- 本次目标：让 `rl-mec-dashboard` 支持展示每个算法的 reward 随 step 变化的收敛曲线，并支持点击/选择算法切换。
- 总模块数：13
- 已完成模块：1-12
- 新增模块：13
- 历史完成步骤数：62
- 新增步骤数：8
- 预计总步骤数：70
- 当前待执行步骤数：0
- 建议开发顺序：模块 13 Step 1-8
- 创建日期：2026-04-28
- 最后更新：2026-05-02

### 变更记录

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v1 | 2026-04-28 | 初始完成 `rl-mec-dashboard` 对 `paper2` 新实验编排架构的迁移：实验状态、artifact 日志、benchmark export、API、前端、测试与文档。 |
| v2 | 2026-05-01 | 适配 `paper2` Patch 10 的 backup/archive 目录语义，避免 dashboard 将备份实验目录误识别为 active run，并新增只读备份归档展示能力。 |
| v3 | 2026-05-01 | 修复实际 VSCode backup 产物看板不可见问题，新增 backup 发现诊断与 archive-only 发现；新增受控本地源文件删除能力。 |
| v3.1 | 2026-05-02 | 根据用户反馈整理前端视觉层级与模块组织：监控主线前置，备份/算法/结果/日志/Danger Zone 分层展示。 |
| v3.2 | 2026-05-02 | 整理本地验证环境：关闭 8093 测试服务，恢复 8088 正式服务，补齐项目 venv 的 Playwright fallback。 |
| v4 | 2026-05-02 | 对接 `paper2` 新增的 `convergence_by_seed` benchmark 字段，在 dashboard 中新增算法收敛性能曲线展示与算法切换交互。 |
| v4.1 | 2026-05-02 | 根据用户验收反馈修复真实实验 convergence 无法加载：当 `benchmark*.json` 缺少 `convergence_by_seed` 时，从 active/backup 实验 artifacts 的 `train_logs.json` 懒加载收敛曲线。 |

---

## Status

### Codex Status Update 2026-05-02

- 当前阶段：模块 13 完成，真实实验 convergence 加载问题已修复，等待 review
- 整体进度：70 / 70 步骤完成
- 状态：NEEDS_REVIEW
- 阻塞项：无
- Last Iteration Summary：模块 13 已完成并补齐真实数据 fallback。后端优先读取 `benchmark*.json` 的 `convergence_by_seed`，缺失时从 active run 或 experiment-backed backup 的 `artifacts/<ALGORITHM>/checkpoints/train_logs.json` 解析 `eval_eval/*` 曲线；archive-only backup 无实验 artifacts 时仍返回 no data。未修改 `paper2` 仓库，未引入 React/Vite，未展示静态 PNG，`/api/runs` payload 保持不变。

> 本区块是项目的实时状态快照。任何 agent（Web 或 Codex）读到此区块即可恢复完整上下文。

### Last Iteration Summary

v3.2 执行结果：模块 11 与模块 12 已完成，并按用户反馈补齐两个行为：backup 现在可作为看板选项进入详情展示，不只出现在备份列表；删除 target 扩展为 dashboard 已识别的本地源文件，包括 active run、backup、archive-only、structured run、legacy log、benchmark export 与全局 `benchmark.json`。前端视觉与信息架构已整理，将运行选择、核心指标、进度和图表前置，将日志合并到底部，将 Danger Zone 下移为低频 destructive 操作区。本地验证环境已整理，8088 正常监听，Playwright fallback 已补齐。`/api/runs` 仍不混入 backup/archive，删除 API 仍只接受 discovery 产生的 `target_id`。

### Pending Decisions

无。收敛曲线第一版只做 `reward vs step` 主图，后端 DTO 预留 `latency`、`energy`、`comm_score` 指标，不在首版 UI 中默认展示四图。

---

## 关键设计原则

1. Active training monitor 主链路已可用，不重做模块 1-12。
2. 不直接嵌入 `paper2` 生成的 `figures/convergence_curves.png`；dashboard 优先使用 benchmark JSON 中的 `convergence_by_seed` 渲染交互式 Chart.js 曲线。
3. 当 benchmark JSON 缺少 `convergence_by_seed` 时，active run 和 experiment-backed backup fallback 到 `artifacts/<ALGORITHM>/checkpoints/train_logs.json`。
4. 第一版 UI 以 `eval/reward_mean` 为默认且必须实现的收敛曲线。
5. 后端解析层必须兼容 `convergence_by_seed` 的 dict 与 list 两种格式。
6. 每个算法支持多 seed 数据；API 返回 per-seed 与 mean/std 聚合曲线。
7. x 轴优先使用 `eval_interval * index`；train log fallback 有 `train_timesteps` 时按点数展开到最终 step。
8. 曲线数据来自当前 selected run 或 selected backup/archive 对应的数据源，不新增数据库。
9. `/api/runs` 不扩大 payload；收敛曲线通过独立 endpoint 懒加载。
10. backup/archive 详情页也必须能查看收敛曲线；archive-only backup 仅在 archive benchmark JSON 包含 `convergence_by_seed` 时有曲线。
11. 前端算法切换必须复用当前 `currentRunState.results` 中的算法列表；无曲线数据的算法置灰或显示 no data。
12. 保持单文件前端，不拆 React/Vite。

## 固定 run id

```text
Full 17 run_id: paper2_full_17_vscode
Quick run_id:   vscode_quick
```

---

# 历史模块状态

## 模块 1-9：paper2 新实验状态机适配

- 当前状态：已完成 `[DONE]`
- 步骤范围：Step 1-42
- 本轮要求：不得重写；只允许因模块 13 测试需要做最小兼容修改。

## 模块 10：Patch 10 备份归档适配

- 当前状态：已完成 `[DONE]`
- 步骤范围：Step 43-48
- 本轮要求：不得回滚；模块 13 需要复用 backup/archive benchmark 读取链路。

## 模块 11：备份可见性修复与诊断增强

- 当前状态：已完成 `[DONE]`
- 步骤范围：Step 49-54
- 本轮要求：保持 `/api/backups/{backup_id}` 能返回 `RunState`；模块 13 只追加收敛曲线 endpoint 与前端调用。

## 模块 12：本地源文件删除功能

- 当前状态：已完成 `[DONE]`
- 步骤范围：Step 55-62
- 本轮要求：不改删除安全策略；仅在删除成功后的刷新链路中补充 convergence UI 清理。

---

# 模块 13：算法收敛性能曲线展示

## 概述

- 职责：解析 `paper2` benchmark JSON 中的 `convergence_by_seed`，为 dashboard 增加每个算法的 reward-step 收敛曲线，并支持点击/选择算法切换。
- 前置依赖：模块 11-12
- 新增步骤数：8
- 影响文件：
  - `dashboard/models.py`
  - `dashboard/convergence.py`（新增）
  - `dashboard/run_discovery.py`
  - `dashboard/api.py`
  - `monitor_dashboard.html`
  - `tests/test_convergence.py`（新增）
  - `tests/test_api_convergence.py`（新增）
  - `tests/test_frontend_convergence_static.py`（新增）
  - `README.md`
  - `docs/progress.md`
  - `docs/report.md`

## Step 1：新增 convergence 领域模型

- **scope: auto**
- 文件：`dashboard/models.py`
- 操作：新增 dataclass：
  ```python
  @dataclass
  class ConvergencePoint:
      step: int
      value: float | None
      seed: str = ""

  @dataclass
  class ConvergenceSeries:
      algorithm: str
      metric: str
      label: str
      eval_interval: int
      seed_series: dict[str, list[ConvergencePoint]] = field(default_factory=dict)
      mean: list[ConvergencePoint] = field(default_factory=list)
      std: list[ConvergencePoint] = field(default_factory=list)
      converged: bool = False
      convergence_reason: str = ""

  @dataclass
  class RunConvergencePayload:
      run_id: str
      source_type: str = ""
      metrics: list[str] = field(default_factory=list)
      algorithms: list[str] = field(default_factory=list)
      series: list[ConvergenceSeries] = field(default_factory=list)
      missing_reason: str = ""
  ```
- 规则：
  - `metric` 首版固定支持：`reward`、`latency`、`energy`、`comm_score`。
  - `label` 映射：
    - `reward` → `Reward`
    - `latency` → `Latency / Task`
    - `energy` → `Energy / Task`
    - `comm_score` → `Comm Score`
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.models import ConvergencePoint, ConvergenceSeries, RunConvergencePayload, dataclass_to_dict
  payload = RunConvergencePayload(run_id='r1', algorithms=['GRPO'], series=[
      ConvergenceSeries(algorithm='GRPO', metric='reward', label='Reward', eval_interval=1000, mean=[
          ConvergencePoint(step=0, value=1.0)
      ])
  ])
  assert dataclass_to_dict(payload)['series'][0]['mean'][0]['step'] == 0
  PY
  ```

## Step 2：新增 convergence 解析服务

- **scope: review**
- 文件：`dashboard/convergence.py`（新增）
- 操作：实现以下函数：
  ```python
  PAPER2_CONVERGENCE_METRICS = {
      "reward": "eval/reward_mean",
      "latency": "eval/latency_mean",
      "energy": "eval/energy_mean",
      "comm_score": "eval/comm_score",
  }

  def load_convergence_payload(
      run_id: str,
      source_type: str,
      benchmark_results: list[dict],
      metric: str = "reward",
  ) -> RunConvergencePayload:
      ...

  def parse_algorithm_convergence(
      record: dict,
      metric: str,
  ) -> ConvergenceSeries | None:
      ...

  def aggregate_seed_series(
      algorithm: str,
      metric: str,
      seed_rows: dict[str, dict],
  ) -> ConvergenceSeries:
      ...

  def detect_convergence(mean_values: list[float | None]) -> tuple[bool, str]:
      ...
  ```
- 解析规则：
  1. 输入是 benchmark JSON 的原始 list[dict]，不是 `AlgorithmResult`，因为 `AlgorithmResult` 当前不保留 `convergence_by_seed`。
  2. 每个 record 必须有 `algorithm`。
  3. `convergence_by_seed` 支持：
     - dict 格式：`{"42": {"eval/reward_mean": [...], "eval_interval": 1000}}`
     - list 格式：`[{"eval/reward_mean": [...], "eval_interval": 1000}]`
  4. `eval_interval` 优先级：
     - seed data 中的 `eval_interval`
     - record 顶层 `eval_interval`
     - 默认 1000
  5. 对齐多 seed 时取最短非空长度。
  6. `mean[i] = nanmean(seed_values_at_i)`。
  7. `std[i] = nanstd(seed_values_at_i)`。
  8. 非数值、NaN、Inf 转为 `None`，聚合时跳过。
- 收敛判定：
  - 与 `paper2` plot 逻辑保持一致：最后 10% 窗口相对变化率 `< 5%` 判定为已收敛。
  - `len(mean_values) < 3` 时不判定收敛。
  - 返回 reason，例如：`tail relative change 3.2% < 5%`。
- 验证：
  ```bash
  python -m pytest tests/test_convergence.py::test_parse_convergence_by_seed_dict_reward -v
  python -m pytest tests/test_convergence.py::test_parse_convergence_by_seed_list_format -v
  python -m pytest tests/test_convergence.py::test_aggregate_seed_series_aligns_to_shortest_seed -v
  python -m pytest tests/test_convergence.py::test_detect_convergence_uses_tail_window -v
  ```

## Step 3：保留 raw benchmark payload 读取入口

- **scope: auto**
- 文件：`dashboard/run_discovery.py`
- 操作：
  1. 新增函数：
     ```python
     def load_benchmark_payload(json_path: Path) -> list[dict]:
         ...
     ```
  2. 保留现有 `load_benchmark_results(json_path)` 行为不变。
  3. `load_benchmark_payload()` 只做 JSON 读取与 list[dict] 过滤，不转换为 `AlgorithmResult`。
- 实现规则：
  - 文件不存在返回 `[]`。
  - JSON 非 list 返回 `[]`。
  - list 中非 dict 项过滤。
  - JSON 格式错误抛 `ValueError`，由 API 层转换为 degraded/missing response。
- 验证：
  ```bash
  python -m pytest tests/test_convergence.py::test_load_benchmark_payload_preserves_convergence_by_seed -v
  python -m pytest tests/test_run_discovery_experiments.py -v
  ```

## Step 4：新增 run / backup convergence API

- **scope: review**
- 文件：`dashboard/api.py`
- 操作：新增 endpoint：
  ```python
  @app.get("/api/runs/{run_id}/convergence")
  async def get_run_convergence(run_id: str, metric: str = "reward"):
      ...

  @app.get("/api/backups/{backup_id}/convergence")
  async def get_backup_convergence(backup_id: str, metric: str = "reward"):
      ...
  ```
- run 数据源规则：
  1. `store.get_run_state(run_id)` 不存在 → HTTP 404。
  2. 优先读取当前 state 的 `benchmark_export_path`。
  3. 若 `benchmark_export_path` 不存在或为空，读取 `benchmark_export_path(store.config, run_id)`。
  4. benchmark payload 无 `convergence_by_seed` 时，fallback 到当前实验目录的 `artifacts/<ALGORITHM>/checkpoints/train_logs.json`。
  5. 若仍无数据，返回：
     ```json
     {
       "run_id": "paper2_full_17_vscode",
       "source_type": "experiment_state",
       "metrics": ["reward"],
       "algorithms": [],
       "series": [],
       "missing_reason": "benchmark export has no convergence_by_seed and train_logs.json has no convergence metric data"
     }
     ```
- backup/archive 数据源规则：
  1. 复用现有 `_find_backup(store, backup_id)`。
  2. 对 experiment backup，读取 `_first_backup_benchmark_file(backup)`。
  3. 对 archive-only backup，读取 `backup.benchmark_archive_dir` 下所有 `benchmark*.json`，合并 list。
  4. experiment backup 的 benchmark payload 无 `convergence_by_seed` 时，fallback 到 backup 实验目录的 `artifacts/<ALGORITHM>/checkpoints/train_logs.json`。
  5. archive-only backup 无实验目录，只有 archive benchmark JSON 含 `convergence_by_seed` 时才有曲线。
  6. 返回 `source_type = "backup"` 或 `"archive"`。
- metric 参数规则：
  - 允许：`reward`、`latency`、`energy`、`comm_score`。
  - 不支持的 metric 返回 HTTP 400。
- 验证：
  ```bash
  python -m pytest tests/test_api_convergence.py::test_run_convergence_returns_reward_series -v
  python -m pytest tests/test_api_convergence.py::test_run_convergence_returns_empty_payload_without_convergence_data -v
  python -m pytest tests/test_api_convergence.py::test_backup_convergence_reads_archive_benchmark_json -v
  python -m pytest tests/test_api_convergence.py::test_convergence_rejects_unknown_metric -v
  ```

## Step 5：前端新增 Convergence 面板

- **scope: review**
- 文件：`monitor_dashboard.html`
- 操作：
  1. 在 `charts-grid` 后、Backups 面板前新增 section：
     ```html
     <section class="panel convergence-panel">
       <h2>
         <span data-i18n="convergence.title">Convergence</span>
         <button class="mini-btn" onclick="loadConvergence()" data-i18n="action.refreshConvergence">Refresh Convergence</button>
       </h2>
       <div class="convergence-controls">
         <select id="convergence-metric" onchange="loadConvergence()">
           <option value="reward">Reward</option>
           <option value="latency">Latency</option>
           <option value="energy">Energy</option>
           <option value="comm_score">Comm Score</option>
         </select>
         <div id="convergence-algorithm-tabs" class="algorithm-tabs"></div>
       </div>
       <div id="convergence-empty" class="muted"></div>
       <div class="chart-container convergence-chart-container">
         <canvas id="convergenceChart"></canvas>
       </div>
     </section>
     ```
  2. 新增前端状态：
     ```js
     convergencePayload: null,
     selectedConvergenceAlgorithm: "",
     charts: {
       ...
       convergenceChart: null
     }
     ```
  3. 新增函数：
     ```js
     async function loadConvergence() { ... }
     function currentConvergenceEndpoint() { ... }
     function renderConvergenceControls(payload) { ... }
     function selectConvergenceAlgorithm(algorithm) { ... }
     function renderConvergenceChart() { ... }
     function destroyConvergenceChart() { ... }
     ```
- endpoint 选择规则：
  - 当前选中普通 run：`/api/runs/{runId}/convergence?metric=reward`
  - 当前选中 backup/archive：`/api/backups/{backupId}/convergence?metric=reward`
  - 判断方式复用现有 selected source 类型；不得用字符串猜路径。
- UI 行为：
  - 默认选中第一个有 series 的算法。
  - 算法 tabs 显示：算法名 + `✓` 收敛标记。
  - 点击算法 tab 后只重绘当前算法曲线。
  - Chart.js datasets：
    - mean 曲线：`payload.series[].mean`
    - seed 曲线：默认隐藏或半透明显示；实现上可先只展示 mean，seed 放入 tooltip 或后续开关。
    - std 可用 tooltip 展示，不强制 fill band。
  - 无数据时显示：`No convergence data found in benchmark JSON or train logs.`
- 验证：
  ```bash
  python -m pytest tests/test_frontend_convergence_static.py::test_frontend_contains_convergence_panel_and_chart -v
  python -m pytest tests/test_frontend_convergence_static.py::test_frontend_has_convergence_endpoint_switch_for_backup_and_run -v
  ```

## Step 6：把 convergence 加入选中 run 刷新链路

- **scope: auto**
- 文件：`monitor_dashboard.html`
- 操作：
  1. 修改 `selectRun(runId)`：完成 run state 初始加载后调用 `loadConvergence()`。
  2. 修改 backup View 操作对应的选择函数：选中 backup 后调用 `loadConvergence()`。
  3. 修改 `confirmDeleteTarget()` 删除成功后：
     - 清空 `convergencePayload`
     - 清空 `selectedConvergenceAlgorithm`
     - 调用 `destroyConvergenceChart()`
     - 若自动选中剩余 run，则重新 `loadConvergence()`
  4. 修改 SSE snapshot 更新：不要每秒重复拉 convergence；只在 run 切换、metric 切换、手动 refresh 时加载。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_convergence_static.py::test_frontend_loads_convergence_after_run_selection -v
  python -m pytest tests/test_frontend_delete_static.py::test_frontend_refreshes_runs_backups_and_delete_targets_after_confirm -v
  ```

## Step 7：测试数据与 API 单测补齐

- **scope: auto**
- 文件：
  - `tests/test_convergence.py`
  - `tests/test_api_convergence.py`
- 操作：
  1. 在 `tests/test_convergence.py` 内构造 `_mock_benchmark_results_with_convergence()`：
     ```python
     [
       {
         "algorithm": "GRPO",
         "convergence_by_seed": {
           "42": {
             "eval/reward_mean": [-10.0, -8.0, -6.0, -5.5, -5.3],
             "eval/latency_mean": [0.5, 0.4, 0.35, 0.33, 0.32],
             "eval/energy_mean": [1.0, 0.9, 0.85, 0.82, 0.81],
             "eval/comm_score": [10.0, 12.0, 14.0, 14.5, 14.8],
             "eval_interval": 1000,
             "total_timesteps": 5000
           }
         }
       }
     ]
     ```
  2. API 测试使用临时 `results/benchmark_<run_id>.json` 和 `results/archive/<timestamp>/benchmark_<run_id>.json`。
  3. 断言返回结构包含：
     - `run_id`
     - `metrics`
     - `algorithms`
     - `series[0].algorithm`
     - `series[0].metric`
     - `series[0].mean[0].step`
     - `series[0].mean[0].value`
- 验证：
  ```bash
  python -m pytest tests/test_convergence.py tests/test_api_convergence.py -v
  ```

## Step 8：文档、进度与全量回归

- **scope: review**
- 文件：
  - `README.md`
  - `docs/plan.md`
  - `docs/progress.md`
  - `docs/report.md`
- 操作：
  1. README 增加“Convergence 曲线”说明：
     - 来源字段：`convergence_by_seed`
     - fallback 来源：active/backup 实验 artifacts 内的 `train_logs.json`
     - 支持 run 与 experiment-backed backup；archive-only 仅支持含 `convergence_by_seed` 的 benchmark archive。
     - 支持算法切换。
  2. 更新 `docs/progress.md`：
     - 新增模块 13 Step 1-8。
  3. 更新 `docs/report.md`：
     - `STATUS: NEEDS_REVIEW`
     - Completed 标记模块 13 auto 步骤。
     - Review Required 标记模块 13 Step 2/4/5/8。
  4. 更新 `docs/plan.md` Status：
     - 当前阶段：模块 13 完成，等待 review
     - 整体进度：70 / 70
     - 状态：NEEDS_REVIEW
- 全量验证：
  ```bash
  python -m pytest tests/test_convergence.py tests/test_api_convergence.py tests/test_frontend_convergence_static.py -v
  python -m pytest tests/test_run_discovery_experiments.py tests/test_api_experiments.py tests/test_delete_service.py tests/test_api_delete.py -v
  python -m pytest -v
  ```
- 手动验收：
  ```bash
  python serve_dashboard.py --port 8088 --experiments-dir <paper2>/experiments --results-dir <paper2>/results --figures-dir <paper2>/figures
  ```
  浏览器打开：
  ```text
  http://127.0.0.1:8088
  ```
  检查：
  1. 选择 `paper2_full_17_vscode`。
  2. Convergence 面板出现。
  3. 默认展示 GRPO 或第一个有 convergence 数据的算法。
  4. 点击 PPO/SAC/其他算法 tab 后曲线切换。
  5. 选择 experiment-backed backup 数据源后，即使 archive benchmark JSON 缺少 `convergence_by_seed`，也可从 backup `train_logs.json` 显示曲线。
  6. archive-only 旧 benchmark JSON 无 convergence 数据时，页面显示 no data，不报 JS 错误。

---

## 模块 13 验收标准

- [x] `/api/runs/{run_id}/convergence?metric=reward` 可返回当前 run 的 reward-step 曲线。
- [x] `/api/backups/{backup_id}/convergence?metric=reward` 可返回 backup/archive benchmark JSON 或 experiment-backed backup train logs 中的 reward-step 曲线。
- [x] API 能兼容 `convergence_by_seed` dict 与 list 两种格式。
- [x] 多 seed 数据能输出 mean/std，并按 `eval_interval` 或 `train_timesteps` 生成 step。
- [x] 前端新增 Convergence 面板。
- [x] 点击算法 tab 后曲线切换，不刷新整个页面。
- [x] 无 convergence 数据时 UI 友好提示，不影响现有 Reward Comparison / Training Time / Backups / Danger Zone。
- [x] 删除当前数据源后 convergence chart 被清空或重载，不显示已删除数据。
- [x] 全量 pytest 通过。

---

## Codex 执行注意事项

1. 本 patch 只对接 `paper2` 已生成的 `benchmark*.json` 与实验 artifacts；不要修改 `paper2` 仓库。
2. 不引入新前端构建系统。
3. 不把 convergence 数据塞入 `/api/runs` 列表，避免 run overview payload 变大。
4. `AlgorithmResult` 可以保持轻量，不强制把 `convergence_by_seed` 或 train-log 曲线放进每个 result；推荐通过 `dashboard/convergence.py` 从 raw payload 懒加载解析。
5. `backup/archive` 的 convergence endpoint 复用现有 backup discovery，不新增第二套 archive scan。
6. 首版 UI 默认只显示 reward；metric 下拉虽支持四项，但验收重点是 reward 随 step 变化。
7. 所有新增 Step 必须按 `scope` 处理：
   - `auto`：Step 1/3/6/7
   - `review`：Step 2/4/5/8
   - `escalate`：无
