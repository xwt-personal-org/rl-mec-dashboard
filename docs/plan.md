# 开发计划：rl-mec-dashboard 对齐 paper2 Patch 10 实验备份与 Fresh 自动保护

## 元信息

- 项目：`rl-mec-dashboard`
- 仓库：`w2030298-art/rl-mec-dashboard`
- 版本：v2
- 计划类型：已有项目迁移改造计划 — Iter merge-back
- 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。
- 当前架构基线：后端已模块化为 `dashboard/` 包，并已支持 `paper2` 新实验状态机：`experiments/<run_id>/run.json`、`state.json`、`artifacts/<ALGORITHM>/{stdout.log,stderr.log,result.json}`、`results/benchmark_<run_id>.json`。
- 本次变更来源：`paper2` Patch 10 — 实验数据备份与 Fresh 自动保护。
- 总模块数：10
- 预计步骤总数：48
- 已完成步骤数：48
- 待执行步骤数：0
- 建议开发顺序：模块 10 Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6
- 创建日期：2026-04-28
- 最后更新：2026-05-01

### 变更记录

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v1 | 2026-04-28 | 初始完成 `rl-mec-dashboard` 对 `paper2` 新实验编排架构的迁移：实验状态、artifact 日志、benchmark export、API、前端、测试与文档。 |
| v2 | 2026-05-01 | 适配 `paper2` Patch 10 的 backup/archive 目录语义，避免 dashboard 将备份实验目录误识别为 active run，并新增只读备份归档展示能力。 |

## Status

> 本区块是项目的实时状态快照。任何 agent（Web 或 Codex）读到此区块即可恢复完整上下文。

- 当前阶段：模块 10 完成，等待 review
- 整体进度：48 / 48 步骤完成
- 状态：NEEDS_REVIEW
- 阻塞项：无
- 当前风险：模块 10 中 Step 2、Step 3、Step 5、Step 6 为 scope:review，需人工确认 active discovery 排除逻辑、backup metadata discovery、只读 API 与前端只读边界。

### Last Iteration Summary

v2 执行结果：已完成模块 10。dashboard 现在识别 `experiments/<run_id>_(backup|auto)_<timestamp>/` 为历史备份并从 active run discovery 排除，新增 `BackupSnapshot`、backup/archive discovery、figures archive enrichment、只读 `/api/backups` 与 `/api/runs/{run_id}/backups`，前端展示当前 run 的 latest backup 信息且不提供 restore/delete/fresh 写操作。全量验证 `python -m pytest -v` 通过。

### Pending Decisions

无。dashboard 本轮仍保持只读，不实现 fresh、delete、restore、start、stop 训练操作。

## 关键迁移原则

1. `experiments/<run_id>/state.json` 仍是 active run 的唯一实时状态源。
2. `experiments/<run_id>_(backup|auto)_<timestamp>/` 是历史备份，不是 active run。
3. 备份目录可展示为 archive metadata，但不得覆盖同名 active run 的 `RunState`。
4. `results/archive/<timestamp>/benchmark*.json` 是历史 benchmark 快照，不得替代 `results/benchmark_<run_id>.json` 的 active export。
5. `results/benchmark.json` 仍只是 latest alias，不得用于判断当前实验状态。
6. dashboard 继续保持只读：不删除、不恢复、不启动、不 fresh。
7. legacy fallback 保留；新 Patch 10 规则仅作用于 `experiments/` 和 `results/archive/` 发现逻辑。

## 固定 run id

```text
Full 17 run_id: paper2_full_17_vscode
Quick run_id:   vscode_quick
```

Full 17 算法顺序必须固定为：

```text
GRPO, PPO, SAC, DDQN, DDPG, TD3, A3C, TRPO, SimPO, MAPPO, QMIX, COMA, IPPO, VDN, MADDPG, IQL, MATD3
```

Quick 算法顺序必须固定为：

```text
GRPO, PPO, SAC
```

---

## 模块 1：配置入口与路径约定迁移

### 概述

- 职责：把 dashboard 的运行配置从旧 `runs_dir` / `logs_dir` / `benchmark_json` 模式扩展为新 `experiments_dir` + `results_dir` 模式，同时保留旧参数兼容。
- 前置依赖：无
- 预计步骤数：5
- 当前状态：已完成

### Step 1：扩展 `DashboardConfig`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/config.py` 已新增 `experiments_dir`、`results_dir`、`default_run_id`、`quick_run_id`、`log_tail_bytes`、`json_retry_keep_last`。
- 验证：`python -m pytest tests/test_config.py -v`

### Step 2：更新 CLI 参数解析
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/config.py::parse_cli_args()` 已支持 `--experiments-dir`、`--results-dir`、`--default-run-id`、`--quick-run-id`、`--log-tail-bytes`。
- 验证：`python serve_dashboard.py --help`

### Step 3：更新 `serve_dashboard.py`
- **scope: auto**
- **[DONE]**
- 操作：`serve_dashboard.py` 保持薄入口，只调用 `parse_cli_args()` 与 `create_app(config)`。
- 验证：`python serve_dashboard.py --help`

### Step 4：定义固定结果路径 helper
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/config.py::benchmark_export_path(config, run_id)` 已返回 `config.results_dir / f"benchmark_{run_id}.json"`。
- 验证：`python -m pytest tests/test_config.py::test_benchmark_export_path -v`

### Step 5：添加配置测试
- **scope: auto**
- **[DONE]**
- 操作：`tests/test_config.py` 已覆盖默认配置、新 CLI 参数、legacy runs_dir 兼容、benchmark export 路径。
- 验证：`python -m pytest tests/test_config.py -v`

---

## 模块 2：领域模型对齐 paper2 实验状态机

### 概述

- 职责：把后端内部 DTO 从旧 run/progress 模型扩展为 experiment/state/algorithm record 模型，并兼容旧 API 字段。
- 前置依赖：模块 1
- 预计步骤数：5
- 当前状态：已完成

### Step 1：扩展状态枚举
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py` 已新增 `ExperimentStatus`、`AlgorithmStatus`、`SourceType`，并扩展 `RunStatus`。
- 验证：`python -c "from dashboard.models import ExperimentStatus, AlgorithmStatus"`

### Step 2：新增算法记录模型
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py::AlgorithmRunRecord` 已支持每算法状态、attempts、artifact 路径、错误与 `result_missing`。
- 验证：`python -c "from dashboard.models import AlgorithmRunRecord; r=AlgorithmRunRecord(name='GRPO'); assert r.status == 'pending'"`

### Step 3：新增实验清单与实验状态模型
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py` 已新增 `AlgorithmSpec`、`ExperimentRunManifest`、`ExperimentStateSnapshot`。
- 验证：`python -c "from dashboard.models import ExperimentRunManifest, ExperimentStateSnapshot"`

### Step 4：扩展 `AlgorithmResult`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py::AlgorithmResult` 已新增 seed、device、train_timesteps、checkpoint_dir、result_path、final_eval。
- 验证：`python -m pytest tests/test_experiment_reader.py::test_read_algorithm_result_maps_final_eval -v`

### Step 5：扩展 `RunState`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py::RunState` 已新增 records、current_index、run/state/process/benchmark 路径、process marker 与 stale marker 字段。
- 验证：`python -c "from dashboard.models import RunState; s=RunState(run_id='x'); assert isinstance(s.records, list)"`

---

## 模块 3：新增 paper2 实验文件读取器

### 概述

- 职责：以只读、容错方式读取 `experiments/<run_id>/` 下的 `run.json`、`state.json`、`process.json`、artifact logs、单算法 `result.json`。
- 前置依赖：模块 2
- 预计步骤数：7
- 当前状态：已完成

### Step 1：创建 `dashboard/experiment_reader.py`
- **scope: auto**
- **[DONE]**
- 操作：已创建 `dashboard/experiment_reader.py`，定义 `safe_read_json_file()`、`read_text_tail()`、`Paper2ExperimentReader`。
- 验证：`python -c "from dashboard.experiment_reader import Paper2ExperimentReader, safe_read_json_file, read_text_tail"`

### Step 2：实现原子写容错读取
- **scope: auto**
- **[DONE]**
- 操作：`safe_read_json_file(path)` 已处理 missing、empty、invalid JSON 与读取异常。
- 验证：`python -m pytest tests/test_experiment_reader.py::test_safe_read_json_file_handles_missing_empty_invalid -v`

### Step 3：实现日志尾部读取
- **scope: auto**
- **[DONE]**
- 操作：`read_text_tail(path, max_bytes)` 已支持大文件尾部读取与 UTF-8 replacement decode。
- 验证：`python -m pytest tests/test_experiment_reader.py::test_read_text_tail_limits_large_log -v`

### Step 4：实现 `Paper2ExperimentReader.__init__`
- **scope: auto**
- **[DONE]**
- 操作：已定义 run/state/process/artifacts 路径 helper。
- 验证：`python -m pytest tests/test_experiment_reader.py::test_reader_paths -v`

### Step 5：实现 `read_run_manifest()`
- **scope: auto**
- **[DONE]**
- 操作：已按 `run.json.algorithms` 顺序转换 `AlgorithmSpec`。
- 验证：`python -m pytest tests/test_experiment_reader.py::test_read_run_manifest_preserves_algorithm_order -v`

### Step 6：实现 `read_state_snapshot()`
- **scope: auto**
- **[DONE]**
- 操作：已读取 `state.json.records`，并按规则生成 stdout/stderr/result 路径；running 记录忽略旧 error。
- 验证：
  ```bash
  python -m pytest tests/test_experiment_reader.py::test_read_state_snapshot_generates_paths -v
  python -m pytest tests/test_experiment_reader.py::test_running_record_ignores_stale_error -v
  ```

### Step 7：实现 `read_algorithm_result()`
- **scope: auto**
- **[DONE]**
- 操作：已将 `final_eval` 常见指标映射到 `AlgorithmResult`，并保留原始 `final_eval`。
- 验证：
  ```bash
  python -m pytest tests/test_experiment_reader.py::test_read_algorithm_result_maps_final_eval -v
  python -m pytest tests/test_experiment_reader.py::test_completed_record_missing_result_is_reported -v
  ```

---

## 模块 4：实验发现与状态聚合改造

### 概述

- 职责：让 dashboard 优先发现 `experiments/<run_id>/`，并基于 `state.json` 合成 `RunSummary` 与 `RunState`。
- 前置依赖：模块 1、2、3
- 预计步骤数：7
- 当前状态：已完成；本次 v2 在模块 10 中追加 Patch 10 backup/archive 适配，不直接重开模块 4。

### Step 1：扩展 `RunDescriptor`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/models.py::RunDescriptor` 已新增 experiment/run/state/process/benchmark/is_placeholder 字段。
- 验证：`python -c "from dashboard.models import RunDescriptor; d=RunDescriptor(run_id='x', source_type='experiment_state'); assert d.source_type == 'experiment_state'"`

### Step 2：实现 `discover_experiment_runs()`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/run_discovery.py::discover_experiment_runs()` 已扫描 `experiments_dir` 下含 `run.json` 或 `state.json` 的目录。
- 验证：`python -m pytest tests/test_run_discovery_experiments.py::test_discover_experiment_runs_finds_state_json -v`

### Step 3：保留默认入口 placeholder
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/run_discovery.py::default_experiment_placeholders()` 已为 Full 17 与 Quick 生成默认入口。
- 验证：`python -m pytest tests/test_run_discovery_experiments.py::test_default_placeholders_are_added_when_files_missing -v`

### Step 4：更新 `discover_runs(config)` 优先级
- **scope: auto**
- **[DONE]**
- 操作：`discover_runs(config)` 已按 experiment_state → legacy_structured → legacy_log → placeholder 合并。
- 验证：`python -m pytest tests/test_run_discovery_experiments.py::test_experiment_descriptor_wins_over_legacy_same_run_id -v`

### Step 5：实现 `RunStateAggregator.scan_experiment_once()`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/state_aggregator.py::RunStateAggregator.scan_experiment_once()` 已从 manifest/snapshot 合成 `RunState`。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py::test_scan_experiment_once_builds_run_state_from_state_json -v`

### Step 6：读取 completed 算法 `result.json`
- **scope: auto**
- **[DONE]**
- 操作：completed record 会读取 per-algorithm `result.json`；缺失时标记 `result_missing=True` 并追加 warn。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py::test_completed_missing_result_sets_result_missing_warning -v`

### Step 7：更新 `scan_once()` 分派逻辑
- **scope: auto**
- **[DONE]**
- 操作：`scan_once()` 已对 `experiment_state` 和 `placeholder` 分派到新实验聚合逻辑。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py tests/test_run_discovery_experiments.py -v`

---

## 模块 5：API 层适配新实验视图与日志读取

### 概述

- 职责：在现有 FastAPI API 上暴露新实验状态、日志 tail、benchmark export，并保持原 `/api/runs`、`/api/runs/{run_id}` 不破坏。
- 前置依赖：模块 4
- 预计步骤数：6
- 当前状态：已完成；本次 v2 在模块 10 中追加备份归档只读 API。

### Step 1：扩展 `/api/health`
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/api.py` 已返回 `version: "0.3.0"`、`has_experiment_state`、run_count、default/quick run id。
- 验证：`python -m pytest tests/test_api_experiments.py::test_health_reports_experiment_state_support -v`

### Step 2：保持 `/api/runs` 返回列表并增加默认入口信息
- **scope: auto**
- **[DONE]**
- 操作：`/api/runs` 已返回 run summary，并包含 `display_name`、`source_type`、`is_placeholder`。
- 验证：`python -m pytest tests/test_api_experiments.py::test_list_runs_contains_full17_and_quick_placeholders -v`

### Step 3：扩展 `/api/runs/{run_id}` 详情
- **scope: auto**
- **[DONE]**
- 操作：`/api/runs/{run_id}` 已返回 `records[]`、artifact 路径、result missing、process/stale marker。
- 验证：`python -m pytest tests/test_api_experiments.py::test_get_run_detail_contains_records_and_artifact_paths -v`

### Step 4：新增日志 tail API
- **scope: auto**
- **[DONE]**
- 操作：已新增 `/api/runs/{run_id}/logs/{algorithm}/stdout` 与 `/stderr`。
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_stdout_log_endpoint_returns_tail -v
  python -m pytest tests/test_api_experiments.py::test_missing_log_endpoint_returns_exists_false -v
  ```

### Step 5：新增 benchmark export API
- **scope: auto**
- **[DONE]**
- 操作：已新增 `/api/runs/{run_id}/benchmark`，空数组有效，文件缺失不 500。
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_benchmark_export_empty_array_is_valid -v
  python -m pytest tests/test_api_experiments.py::test_missing_benchmark_export_is_not_500 -v
  ```

### Step 6：SSE 继续推送 run snapshot
- **scope: auto**
- **[DONE]**
- 操作：`/api/runs/{run_id}/events` 已对 experiment run 返回 SSE snapshot。
- 验证：`python -m pytest tests/test_api_experiments.py::test_sse_endpoint_exists_for_experiment_run -v`

---

## 模块 6：前端 `monitor_dashboard.html` 迁移

### 概述

- 职责：单页前端展示固定入口、算法状态表、artifact 日志、进度、结果、benchmark 图表与对比。
- 前置依赖：模块 5
- 预计步骤数：6
- 当前状态：已完成；本次 v2 在模块 10 中追加备份状态展示。

### Step 1：更新前端数据模型常量
- **scope: auto**
- **[DONE]**
- 操作：`monitor_dashboard.html` 已支持新状态、source type、i18n 文案。
- 验证：`python -m pytest tests/test_frontend_static.py -v`（如本仓库无该文件，则运行全量测试）

### Step 2：首页增加固定入口卡片
- **scope: auto**
- **[DONE]**
- 操作：首页 run overview 已展示 Full 17 与 Quick placeholder。
- 验证：`python -m pytest tests/test_api_experiments.py::test_list_runs_contains_full17_and_quick_placeholders -v`

### Step 3：实现算法状态表
- **scope: auto**
- **[DONE]**
- 操作：前端已展示 `records[]` 状态、attempts、device、started/finished、result missing、日志按钮、error。
- 验证：人工打开 dashboard，检查 Full 17 / Quick 状态表。

### Step 4：实现 stdout/stderr 日志面板
- **scope: auto**
- **[DONE]**
- 操作：前端已通过日志 tail API 加载当前算法 stdout/stderr。
- 验证：`python -m pytest tests/test_api_experiments.py::test_stdout_log_endpoint_returns_tail -v`

### Step 5：实验证进度与 stale marker 展示
- **scope: auto**
- **[DONE]**
- 操作：前端已展示 progress、overall progress、process marker、possibly stale。
- 验证：人工打开带 `process.json` 的 fixture 页面。

### Step 6：更新结果与图表渲染
- **scope: auto**
- **[DONE]**
- 操作：结果表和 Chart.js 图表已读取 `results` 与 `/api/runs/{run_id}/benchmark`。
- 验证：`python -m pytest tests/test_api_experiments.py::test_fixture_api_end_to_end -v`

---

## 模块 7：benchmark 兼容与导出映射

### 概述

- 职责：兼容 `paper2` 导出的 `results/benchmark_<run_id>.json` 与旧 benchmark 字段。
- 前置依赖：模块 4、5
- 预计步骤数：3
- 当前状态：已完成

### Step 1：更新 benchmark loader 字段映射
- **scope: auto**
- **[DONE]**
- 操作：`dashboard/run_discovery.py::load_benchmark_results()` 已支持 `final_reward_mean`、`final_latency_mean`、`final_energy_mean`、`final_comm_score` 等字段。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py::test_benchmark_export_supplements_missing_metric_without_overriding_result_json -v`

### Step 2：状态聚合中按 run_id 读取 benchmark export
- **scope: auto**
- **[DONE]**
- 操作：`scan_experiment_once()` 已按 descriptor 的 `benchmark_export_file` 合并 fallback benchmark。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py::test_benchmark_export_supplements_missing_metric_without_overriding_result_json -v`

### Step 3：更新 compare/export helper
- **scope: auto**
- **[DONE]**
- 操作：compare/export 使用 `RunState.results`，可对 structured 与 benchmark fallback 结果做对比。
- 验证：`python -m pytest tests/test_exporter.py tests/test_api_experiments.py -v`

---

## 模块 8：测试 fixtures 与回归测试补齐

### 概述

- 职责：提供 Full 17 running、Quick failed、completed result、edge case fixtures。
- 前置依赖：模块 1-7
- 预计步骤数：5
- 当前状态：已完成；本次 v2 在模块 10 中追加 Patch 10 backup/archive fixtures。

### Step 1：创建 Full 17 running fixture
- **scope: auto**
- **[DONE]**
- 操作：`tests/fixtures/experiments/paper2_full_17_vscode/` 已提供 Full 17 状态 fixture。
- 验证：`python -m pytest tests/test_api_experiments.py::test_fixture_api_end_to_end -v`

### Step 2：创建 Quick failed fixture
- **scope: auto**
- **[DONE]**
- 操作：`tests/fixtures/experiments/vscode_quick/` 已提供 Quick failed 状态与日志 fixture。
- 验证：`python -m pytest tests/test_state_aggregator_experiments.py::test_quick_failed_points_to_grpo_logs -v`

### Step 3：创建 completed result fixture
- **scope: auto**
- **[DONE]**
- 操作：已提供 completed per-algorithm `result.json` fixture。
- 验证：`python -m pytest tests/test_experiment_reader.py tests/test_state_aggregator_experiments.py -v`

### Step 4：创建 edge case fixtures
- **scope: auto**
- **[DONE]**
- 操作：已提供 missing result 与 invalid state JSON fixture。
- 验证：
  ```bash
  python -m pytest tests/test_state_aggregator_experiments.py::test_missing_completed_result_is_warning_not_failure -v
  python -m pytest tests/test_state_aggregator_experiments.py::test_invalid_state_json_does_not_crash_scan -v
  ```

### Step 5：端到端 API 测试
- **scope: auto**
- **[DONE]**
- 操作：`tests/test_api_experiments.py` 已覆盖 health、runs、detail、logs、benchmark、SSE、fixture e2e。
- 验证：`python -m pytest tests/test_api_experiments.py -v`

---

## 模块 9：文档、启动脚本与最终验收

### 概述

- 职责：更新 README、Windows 启动脚本、迁移说明和最终验收。
- 前置依赖：模块 1-8
- 预计步骤数：3
- 当前状态：已完成

### Step 1：更新 README
- **scope: auto**
- **[DONE]**
- 操作：README 已说明 dashboard 对 `paper2` 新实验目录的读取方式。
- 验证：`python -m pytest -v`

### Step 2：更新 Windows 启动脚本
- **scope: auto**
- **[DONE]**
- 操作：Windows 启动脚本已适配当前入口。
- 验证：`python -m pytest tests/test_windows_start_menu_scripts.py -v`（如存在）

### Step 3：新增迁移说明文档
- **scope: auto**
- **[DONE]**
- 操作：已新增迁移说明文档。
- 验证：`python -m pytest -v`

---

# 模块 10：Patch 10 备份归档适配（新增）

## 概述

- 职责：让 dashboard 正确理解 `paper2` Patch 10 的备份与归档文件语义。
- 核心问题：
  1. `scripts/backup_experiment.py` 会复制 `experiments/<run_id>/` 到 `experiments/<run_id>_backup_<timestamp>/`。
  2. `start --fresh` 默认会复制到 `experiments/<run_id>_auto_<timestamp>/` 后再删除并重建 active run。
  3. 复制目录内保留原 `run.json.run_id` 与 `state.json.run_id`，dashboard 当前按 `run_id` 建状态缓存，存在覆盖 active run 的风险。
  4. `results/archive/<timestamp>/benchmark*.json` 是历史结果快照，不得替代 active `results/benchmark_<run_id>.json`。
- 前置依赖：模块 1-9 全部完成
- 预计步骤数：6

---

## Step 1：新增 backup/archive 领域模型（新增）

- **scope: auto**
- **[DONE]**
- 文件：`dashboard/models.py`
- 操作：新增 dataclass `BackupSnapshot`。
- 必须定义字段：

```python
@dataclass
class BackupSnapshot:
    run_id: str
    backup_id: str
    backup_type: str
    timestamp: str
    experiment_dir: str
    display_name: str = ""
    source_run_id: str = ""
    status: str = ""
    completed_algorithms: int = 0
    total_algorithms: int = 0
    created_at: str = ""
    updated_at: str = ""
    benchmark_archive_dir: str = ""
    benchmark_files: list[str] = field(default_factory=list)
    figures_archive_dir: str = ""
    figure_files: list[str] = field(default_factory=list)
```

- 字段规则：
  - `backup_type` 只允许 `"backup"` 或 `"auto"`。
  - `backup_id = f"{source_run_id}_{backup_type}_{timestamp}"`。
  - `run_id` 用于 API 路径时等于 `backup_id`，避免与 active run 的 `run_id` 冲突。
  - `source_run_id` 来自备份目录名的原始 run id。
  - `status` 从备份目录内 `state.json.status` 读取；读取失败为空字符串。
  - `completed_algorithms` 从 `state.json.completed_algorithms.length` 读取；读取失败为 0。
  - `total_algorithms` 优先从 `state.json.records.length` 读取，其次从 `run.json.algorithms.length` 读取。
- 同步更新 `dataclass_to_dict()` 无需特殊分支，现有 dataclass 递归逻辑应直接支持。
- 验证：

```bash
python - <<'PY'
from dashboard.models import BackupSnapshot, dataclass_to_dict
b = BackupSnapshot(run_id='paper2_full_17_vscode_backup_20260501_150000', backup_id='paper2_full_17_vscode_backup_20260501_150000', backup_type='backup', timestamp='20260501_150000', experiment_dir='x', source_run_id='paper2_full_17_vscode')
d = dataclass_to_dict(b)
assert d['backup_type'] == 'backup'
assert d['source_run_id'] == 'paper2_full_17_vscode'
PY
```

---

## Step 2：实现 backup 目录识别与 active discovery 排除（已修改）

- **scope: review**
- **[DONE]**
- 文件：`dashboard/run_discovery.py`
- 操作 1：新增常量与函数：

```python
import re

BACKUP_DIR_PATTERN = re.compile(
    r"^(?P<source_run_id>[A-Za-z0-9_.-]+)_(?P<backup_type>backup|auto)_(?P<timestamp>\d{8}_\d{6})$"
)

def parse_backup_dir_name(name: str) -> tuple[str, str, str] | None:
    ...

def is_backup_experiment_dir(path: Path) -> bool:
    ...
```

- 实现要求：
  - `parse_backup_dir_name("paper2_full_17_vscode_backup_20260501_150000")` 返回 `("paper2_full_17_vscode", "backup", "20260501_150000")`。
  - `parse_backup_dir_name("paper2_full_17_vscode_auto_20260501_150000")` 返回 `("paper2_full_17_vscode", "auto", "20260501_150000")`。
  - 对 `paper2_full_17_vscode`、`vscode_quick`、`paper2_full_17_vscode_backup_bad` 返回 `None`。
  - `is_backup_experiment_dir(path)` 只基于 `path.name` 判断，不读取文件。
- 操作 2：修改 `discover_experiment_runs(experiments_dir, results_dir)`：
  - 在遍历 `experiments_dir.iterdir()` 时，若 `is_backup_experiment_dir(experiment_dir)` 为 True，直接 `continue`。
  - 不要把 backup 目录合并成 `RunDescriptor`。
  - 不要让 backup 目录参与 default placeholder skip 逻辑。
- 风险说明：
  - 该步骤影响 active run discovery 与状态缓存，完成后需要重点审核。
- 验证：

```bash
python -m pytest tests/test_run_discovery_experiments.py::test_backup_experiment_dirs_are_excluded_from_active_runs -v
python -m pytest tests/test_run_discovery_experiments.py::test_active_run_wins_when_backup_has_same_embedded_run_id -v
```

---

## Step 3：实现备份归档发现器（新增）

- **scope: review**
- **[DONE]**
- 文件：`dashboard/run_discovery.py`
- 操作：新增函数：

```python
def discover_experiment_backups(experiments_dir: Path | None, results_dir: Path) -> list[BackupSnapshot]:
    ...
```

- 发现规则：
  - `experiments_dir is None` 或目录不存在时返回空列表。
  - 遍历 `experiments_dir.iterdir()`，只接受目录名匹配 `BACKUP_DIR_PATTERN` 的目录。
  - 每个 backup 目录可以存在 `run.json`、`state.json`，但二者都不是必须。
  - `display_name` 优先读取 `run.json.name`；否则使用 `source_run_id`。
  - `status` 优先读取 `state.json.status`；否则为空字符串。
  - `completed_algorithms` 从 `state.json.completed_algorithms` 长度读取。
  - `total_algorithms` 优先从 `state.json.records` 长度读取；其次从 `run.json.algorithms` 长度读取。
  - `created_at`、`updated_at` 优先来自 `run.json` / `state.json`；没有则为空字符串。
  - `experiment_dir` 填 backup 目录字符串路径。
  - `benchmark_archive_dir = str(results_dir / "archive" / timestamp)`，仅当目录存在时填充，否则为空字符串。
  - `benchmark_files` 读取该 archive 目录下顶层 `benchmark*.json` 文件名，按文件名排序；不递归。
  - `figures_archive_dir` 不在本函数内推断，保留为空字符串；图表 archive 由 Step 4 可选补充。
- 排序：
  - 返回列表按 `timestamp` 降序排列；同 timestamp 下按 `backup_id` 升序。
- 禁止：
  - 不读取 `experiments/.index.sqlite3`。
  - 不把 `results/archive` 中的 benchmark 文件合并到 active `RunState.results`。
- 验证：

```bash
python -m pytest tests/test_run_discovery_experiments.py::test_discover_experiment_backups_reads_backup_metadata -v
python -m pytest tests/test_run_discovery_experiments.py::test_discover_experiment_backups_links_result_archive_by_timestamp -v
```

---

## Step 4：可选补充 figures archive 发现（新增）

- **scope: auto**
- **[DONE]**
- 文件：`dashboard/run_discovery.py`
- 操作：新增函数：

```python
def enrich_backup_figures(backups: list[BackupSnapshot], figures_dir: Path | None) -> list[BackupSnapshot]:
    ...
```

- 实现规则：
  - `figures_dir is None` 或目录不存在时直接返回原列表。
  - 对每个 `BackupSnapshot`：
    - `candidate = figures_dir / "archive" / backup.timestamp`
    - 若目录存在：
      - `backup.figures_archive_dir = str(candidate)`
      - `backup.figure_files = sorted(item.name for item in candidate.iterdir() if item.is_file())`
    - 若目录不存在：保持空字符串与空列表。
  - 不递归读取 `figures/archive/<timestamp>/archive`。
- 验证：

```bash
python -m pytest tests/test_run_discovery_experiments.py::test_enrich_backup_figures_reads_top_level_files_only -v
```

---

## Step 5：新增只读 backup API（新增）

- **scope: review**
- **[DONE]**
- 文件：`dashboard/config.py`
- 操作 1：扩展 `DashboardConfig`：
  - 新增字段：`figures_dir: Path | None = Path("figures")`
- 操作 2：扩展 `parse_cli_args(argv)`：
  - 新增参数：`--figures-dir`，默认 `figures`
- 操作 3：更新启动日志（如 `serve_dashboard.py` 当前打印配置）：
  - 打印 `figures_dir`
- 文件：`dashboard/api.py`
- 操作 4：新增 endpoint：

```python
@app.get("/api/backups")
async def list_backups():
    ...

@app.get("/api/runs/{run_id}/backups")
async def list_run_backups(run_id: str):
    ...
```

- API 规则：
  - `/api/backups` 返回：
    ```json
    {
      "backups": [ ...BackupSnapshot dict... ]
    }
    ```
  - `/api/runs/{run_id}/backups` 返回：
    ```json
    {
      "run_id": "paper2_full_17_vscode",
      "backups": [ ...only source_run_id == run_id... ]
    }
    ```
  - 两个接口均只读，不触发文件复制、删除、恢复。
  - 内部调用：
    ```python
    backups = discover_experiment_backups(store.config.experiments_dir, store.config.results_dir)
    backups = enrich_backup_figures(backups, store.config.figures_dir)
    ```
- API 兼容要求：
  - 不修改 `/api/runs` 响应结构。
  - 不修改 `/api/runs/{run_id}` 响应结构。
  - 不把 backup 放入 run overview active list。
- 验证：

```bash
python -m pytest tests/test_config.py::test_default_config_uses_figures_dir -v
python -m pytest tests/test_api_experiments.py::test_list_backups_returns_patch10_backup_snapshots -v
python -m pytest tests/test_api_experiments.py::test_list_run_backups_filters_by_source_run_id -v
```

---

## Step 6：前端展示备份信息与回归验收（新增）

- **scope: review**
- **[DONE]**
- 文件：`monitor_dashboard.html`
- 操作 1：新增 i18n 文案：
  - `backup.title`
  - `backup.latest`
  - `backup.none`
  - `backup.type`
  - `backup.timestamp`
  - `backup.status`
  - `backup.completed`
  - `backup.files`
  - `backup.auto`
  - `backup.manual`
- 操作 2：在前端 `dashboardState` 新增字段：
  ```js
  backups: [],
  currentRunBackups: []
  ```
- 操作 3：新增 API client 函数：
  ```js
  async function loadBackups() { ... }              // GET /api/backups
  async function loadRunBackups(runId) { ... }      // GET /api/runs/{runId}/backups
  ```
- 操作 4：在 Run Detail 或 Progress panel 下方新增一个轻量 Backup panel：
  - 显示当前 run 最新 backup：
    - `backup_type`
    - `timestamp`
    - `status`
    - `completed_algorithms / total_algorithms`
    - `benchmark_files.length`
    - `figure_files.length`
  - 若没有 backup，显示 `backup.none`。
  - 不提供 restore/delete/fresh 按钮。
- 操作 5：Run Overview tile 上可选显示 latest backup timestamp：
  - 只对 active run 显示。
  - placeholder 没有 backup 时不显示警告。
- 操作 6：新增静态或 API 回归测试：
  - 若项目已有前端静态断言测试，追加检查 `backup.title`、`loadRunBackups`、`/api/runs/${runId}/backups` 字符串。
  - 若没有前端静态测试，则新增 `tests/test_frontend_backup_static.py`。
- 验证：

```bash
python -m pytest tests/test_frontend_backup_static.py -v
python -m pytest tests/test_run_discovery_experiments.py tests/test_api_experiments.py -v
python -m pytest -v
```

---

## 模块 10 验收标准

- [x] `experiments/paper2_full_17_vscode_backup_20260501_150000/` 不出现在 `/api/runs`。
- [x] `experiments/paper2_full_17_vscode_auto_20260501_150000/` 不出现在 `/api/runs`。
- [x] 当 active `experiments/paper2_full_17_vscode/` 和 backup 目录同时存在时，`/api/runs/paper2_full_17_vscode` 只读取 active 目录。
- [x] `/api/backups` 返回 backup/auto 两类快照。
- [x] `/api/runs/paper2_full_17_vscode/backups` 只返回 `source_run_id == "paper2_full_17_vscode"` 的备份。
- [x] `results/archive/<timestamp>/benchmark*.json` 只作为 backup metadata 展示，不参与 active charts 自动合并。
- [x] `figures/archive/<timestamp>/*` 只作为 backup metadata 展示，不递归读取旧 archive。
- [x] `python -m pytest -v` 通过。
- [x] dashboard 页面显示 latest backup 信息，但不提供写操作按钮。

---

## Codex 执行注意事项

1. 只执行模块 10 的新增/修改步骤。
2. 模块 1-9 标记 `[DONE]`，不得重写。
3. 修改 `dashboard/run_discovery.py` 时优先保证 active discovery 不受 backup 目录污染。
4. 所有新增 API 保持只读。
5. 若发现当前仓库已有 `tests/test_frontend_static.py`，优先追加测试；否则新增 `tests/test_frontend_backup_static.py`。
6. 若 `docs/report.md` 不存在，执行完成后创建并按 v3 report 模板维护。
7. 每完成一个模块 10 Step，更新 `docs/progress.md` 与 `docs/plan.md` Status。
