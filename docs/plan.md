# 开发计划：rl-mec-dashboard 备份可见性修复与本地实验数据删除

## 元信息

- 项目：`rl-mec-dashboard`
- 仓库：`w2030298-art/rl-mec-dashboard`
- 版本：v3.2
- 计划类型：已有项目迁移改造计划 — Iter merge-back
- 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。
- 当前架构基线：后端已模块化为 `dashboard/` 包，已支持 `paper2` 实验状态机、artifact 日志、benchmark export、Patch 10 backup/archive metadata 展示。
- 本次变更来源：用户手动测试反馈
  - 当前训练数据显示正常。
  - VSCode `Backup Full 17 Data` 生成的备份数据在看板中不可见。
  - 用户希望在看板中删除不需要的本地实验源文件。
- 总模块数：12
- 已完成模块：1-10
- 新增模块：11-12
- 历史完成步骤数：48
- 新增步骤数：14
- 预计总步骤数：62
- 当前待执行步骤数：0
- 建议开发顺序：模块 11 Step 1-6 → 模块 12 Step 1-8
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

## Status

### Codex Status Update 2026-05-02

- 当前阶段：模块 11-12、前端视觉整理与本地验证环境整理完成，等待 review
- 整体进度：62 / 62 步骤完成
- 状态：NEEDS_REVIEW
- 阻塞项：无
- Last Iteration Summary：模块 11 与模块 12 已完成，并按用户反馈补齐两个行为：backup 现在可作为看板选项进入详情展示，不只出现在备份列表；删除 target 扩展为 dashboard 已识别的本地源文件，包括 active run、backup、archive-only、structured run、legacy log、benchmark export 与全局 `benchmark.json`。前端视觉与信息架构已整理，将运行选择、核心指标、进度和图表前置，将日志合并到底部，将 Danger Zone 下移为低频 destructive 操作区。本轮补齐本地验证环境，关闭 8093 测试服务，确认 8088 正常监听，并安装验证 Playwright fallback。`/api/runs` 仍不混入 backup/archive，删除 API 仍只接受 discovery 产生的 `target_id`。

> 本区块是项目的实时状态快照。任何 agent（Web 或 Codex）读到此区块即可恢复完整上下文。

### Last Iteration Summary

v2 执行结果：模块 10 已完成并通过测试，新增 `BackupSnapshot`、backup/auto active discovery 排除、backup discovery、figures archive enrichment、只读 `/api/backups` 与 `/api/runs/{run_id}/backups`。但用户手动测试发现 VSCode `Backup Full 17 Data` 生成的数据在页面不可见。当前实现只扫描 `experiments_dir` 根目录下严格命名为 `<run_id>_(backup|auto)_YYYYMMDD_HHMMSS` 的目录，并且前端只围绕当前 run 展示 latest backup，缺少全局备份视图、路径诊断、archive-only 结果发现和非标准备份路径兼容。

### Pending Decisions

无。删除功能本轮确定加入，但必须以两段式确认、路径白名单和运行中拒删为硬约束。

## 关键设计原则

1. Active training monitor 主链路已可用，不重做模块 1-9。
2. backup 可见性修复不得把 backup 目录重新放回 `/api/runs` active list。
3. `results/archive/<timestamp>/benchmark*.json` 即使没有匹配的 backup experiment directory，也必须可在 backup/archive 页面中被发现。
4. 删除功能删除的是源文件，不是仅隐藏记录。
5. 删除 API 不接受任意文件系统路径，只接受后端 discovery 已返回的 `target_id`。
6. 删除 active run 前必须确认该 run 非 running、无 `process.json`。
7. 删除 backup/archive 前必须展示将删除哪些目录/文件。
8. 不删除 `.git`、项目源码、`docs/`、`dashboard/`、`tests/`、任意父目录。
9. Windows 路径必须兼容。
10. 所有 destructive endpoint 必须有 preview endpoint 与 explicit confirm token。
11. 用户反馈补充：backup 必须能作为 dashboard 可选数据源展示；删除功能覆盖所有 dashboard 已识别的本地源文件，但仍不允许前端/API 传任意路径。

## 固定 run id

```text
Full 17 run_id: paper2_full_17_vscode
Quick run_id:   vscode_quick
```

---

# 历史模块状态

## 模块 1-9：paper2 新实验状态机适配

- 当前状态：已完成
- 步骤范围：Step 1-42
- 本轮要求：不得重写；只允许因模块 11/12 测试需要做最小兼容修改。

## 模块 10：Patch 10 备份归档适配

- 当前状态：已完成但手动测试未通过
- 步骤范围：Step 43-48
- 本轮要求：保留已有实现，作为模块 11 的基础；不要回滚。
- 已知问题：实际 VSCode backup 数据未在看板显示。

---

# 模块 11：备份可见性修复与诊断增强

## 概述

- 职责：修复 VSCode `Backup Full 17 Data` 生成的备份不可见问题；增加全局备份视图与诊断 API。
- 前置依赖：模块 10
- 预计步骤数：6
- 影响文件：
  - `dashboard/config.py`
  - `dashboard/models.py`
  - `dashboard/run_discovery.py`
  - `dashboard/api.py`
  - `monitor_dashboard.html`
  - `tests/test_run_discovery_experiments.py`
  - `tests/test_api_experiments.py`
  - `tests/test_frontend_backup_static.py`
  - `README.md` 或 `docs/windows-start-menu-launcher.md`
  - `docs/report.md`
  - `docs/progress.md`

## Step 1：新增 backup scan roots 配置

- **scope: auto**
- 文件：`dashboard/config.py`
- 操作：
  1. 在 `DashboardConfig` 新增字段：
     ```python
     backup_scan_dirs: list[Path] = field(default_factory=list)
     ```
  2. 修改 `parse_cli_args(argv)`：
     - 新增参数 `--backup-scan-dir`，允许重复传入：
       ```bash
       --backup-scan-dir C:/Users/22003/paper2/experiments
       --backup-scan-dir C:/Users/22003/paper2/backups
       ```
     - 默认值为空列表。
  3. 新增 helper：
     ```python
     def backup_scan_roots(config: DashboardConfig) -> list[Path]:
         ...
     ```
- 实现规则：
  - 返回去重后的扫描根目录。
  - 顺序：
    1. `config.experiments_dir`
    2. `config.results_dir / "archive"` 的父级不作为 experiment backup root，只作为 archive-only root；不要混入此 helper。
    3. `config.backup_scan_dirs`
  - `None` 和不存在目录不在 helper 中强制过滤，由 discovery 函数决定。
- 验证：
  ```bash
  python -m pytest tests/test_config.py::test_backup_scan_dirs_can_be_repeated -v
  python -m pytest tests/test_config.py::test_backup_scan_roots_deduplicates_experiments_dir -v
  ```

## Step 2：扩展 backup 目录命名兼容

- **scope: review**
- 文件：`dashboard/run_discovery.py`
- 操作：
  1. 保留现有严格命名匹配。
  2. 新增宽松识别函数：
     ```python
     def infer_backup_metadata_from_dir(path: Path) -> tuple[str, str, str] | None:
         ...
     ```
  3. 修改 `discover_experiment_backups()` 使用该函数，而不是只调用 `parse_backup_dir_name()`。
- 必须兼容的目录名：
  ```text
  paper2_full_17_vscode_backup_20260501_150000
  paper2_full_17_vscode_auto_20260501_150000
  paper2_full_17_vscode_backup_2026-05-01_15-00-00
  paper2_full_17_vscode_auto_2026-05-01_15-00-00
  paper2_full_17_vscode_backup_20260501-150000
  paper2_full_17_vscode_backup
  ```
- 推断规则：
  - 优先严格正则。
  - 若目录名包含 `_backup_` 或 `_auto_`，按分隔符左侧作为 `source_run_id`，右侧解析 timestamp。
  - 若目录名以 `_backup` 或 `_auto` 结尾且无 timestamp：
    - `timestamp` 使用目录 `st_mtime` 转成 `YYYYMMDD_HHMMSS`。
  - `backup_type` 只允许 `backup` 或 `auto`。
  - 无法推断 `source_run_id` 时，若 `run.json.run_id` 存在，使用 `run.json.run_id`。
- 验证：
  ```bash
  python -m pytest tests/test_run_discovery_experiments.py::test_infer_backup_metadata_accepts_vscode_backup_variants -v
  python -m pytest tests/test_run_discovery_experiments.py::test_backup_without_timestamp_uses_directory_mtime -v
  ```

## Step 3：支持多 backup scan roots

- **scope: review**
- 文件：`dashboard/run_discovery.py`
- 操作：
  1. 新增函数：
     ```python
     def discover_experiment_backups_from_roots(
         roots: list[Path],
         results_dir: Path,
     ) -> list[BackupSnapshot]:
         ...
     ```
  2. 保留现有 `discover_experiment_backups(experiments_dir, results_dir)`，内部委托新函数。
  3. 修改 `dashboard/api.py::_discover_backups(store)` 使用：
     ```python
     roots = backup_scan_roots(store.config)
     backups = discover_experiment_backups_from_roots(roots, store.config.results_dir)
     ```
- 合并规则：
  - `backup_id` 相同只保留一个。
  - 若重复，优先保留包含 `state.json` 的备份目录。
  - 排序按 timestamp 降序。
- 验证：
  ```bash
  python -m pytest tests/test_run_discovery_experiments.py::test_discover_experiment_backups_from_multiple_roots -v
  python -m pytest tests/test_api_experiments.py::test_list_backups_uses_backup_scan_dirs -v
  ```

## Step 4：新增 archive-only 发现

- **scope: review**
- 文件：`dashboard/run_discovery.py`
- 操作：
  1. 新增函数：
     ```python
     def discover_archive_only_backups(results_dir: Path) -> list[BackupSnapshot]:
         ...
     ```
  2. 在 `discover_experiment_backups_from_roots()` 结果之外，API 聚合时追加 archive-only backups。
- 发现规则：
  - 扫描 `results_dir / "archive" / "*"`。
  - 只接受目录。
  - 目录下存在 `benchmark*.json` 时生成 `BackupSnapshot`。
  - `backup_type = "archive"`
  - `source_run_id`：
    - 优先从文件名 `benchmark_<run_id>.json` 提取。
    - `benchmark.json` 不能推断 source_run_id，设为空字符串。
  - `run_id = backup_id = f"{source_run_id or 'unknown'}_archive_{timestamp}"`
  - `timestamp` 优先用 archive 目录名；若目录名不可解析，用目录 `st_mtime`。
  - `experiment_dir = ""`
  - `benchmark_archive_dir = str(archive_dir)`
  - `benchmark_files = sorted(...)`
- 模型调整：
  - `BackupSnapshot.backup_type` 允许 `"archive"`。
- 验证：
  ```bash
  python -m pytest tests/test_run_discovery_experiments.py::test_discover_archive_only_backups_from_results_archive -v
  python -m pytest tests/test_api_experiments.py::test_list_backups_includes_archive_only_snapshots -v
  ```

## Step 5：新增备份诊断 API

- **scope: auto**
- 文件：`dashboard/api.py`
- 操作：新增 endpoint：
  ```python
  @app.get("/api/backups/diagnostics")
  async def backup_diagnostics():
      ...
  ```
- 返回结构：
  ```json
  {
    "experiments_dir": "...",
    "results_dir": "...",
    "figures_dir": "...",
    "backup_scan_dirs": ["..."],
    "scanned_roots": [
      {"path": "...", "exists": true, "entries": 12, "candidate_backups": 2}
    ],
    "results_archive": {
      "path": ".../results/archive",
      "exists": true,
      "entries": 3,
      "benchmark_archives": 2
    },
    "matched_backups": 3,
    "notes": []
  }
  ```
- 规则：
  - 不抛 500；读取失败写入 `notes`。
  - 不返回大文件内容。
- 用户反馈补充展示 API：
  - 新增 `GET /api/backups/{backup_id}`，返回可被现有看板详情渲染的 `RunState`。
  - 新增 `GET /api/backups/{backup_id}/logs/{algorithm}/{stream}`，支持 backup artifact log tail。
  - archive-only backup 通过 `results/archive/<timestamp>/benchmark*.json` 构建静态结果快照。
- 验证：
  ```bash
  python -m pytest tests/test_api_experiments.py::test_backup_diagnostics_reports_scan_roots_and_archive -v
  ```

## Step 6：前端新增全局 Backups 面板与诊断提示

- **scope: review**
- 文件：`monitor_dashboard.html`
- 操作：
  1. 将当前只显示 current run latest backup 的 panel 改成：
     - 当前 run latest backup
     - 全局 recent backups table
     - diagnostics summary
  2. 新增前端函数：
     ```js
     async function loadBackupDiagnostics() { ... }
     function renderGlobalBackups(backups) { ... }
     function renderBackupDiagnostics(diagnostics) { ... }
     ```
  3. 页面上显示：
     - scanned roots
     - results archive 是否存在
     - matched backups 数量
     - 当 matched_backups 为 0 时，显示“检查 --experiments-dir / --backup-scan-dir / --results-dir”
  4. 保留 `/api/runs/{runId}/backups` 当前 run 过滤逻辑。
  5. 将 backup 加入 top-level run selector 的 Backups 分组，并在全局 backups table 提供 View 操作。
- 禁止：
  - 不提供恢复、删除按钮；删除按钮放在模块 12 的 Danger Zone。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_backup_static.py::test_frontend_contains_global_backup_diagnostics_ui -v
  python -m pytest tests/test_frontend_backup_static.py::test_frontend_can_select_backups_as_dashboard_options -v
  python -m pytest tests/test_api_experiments.py::test_list_run_backups_filters_by_source_run_id -v
  ```

## 模块 11 验收标准

- [x] VSCode `Backup Full 17 Data` 生成的标准或非标准命名目录可以被 `/api/backups` 发现。
- [x] `results/archive/<timestamp>/benchmark*.json` 即使没有 experiment backup dir，也能作为 archive-only backup 显示。
- [x] `/api/backups/diagnostics` 能显示实际扫描了哪些目录。
- [x] `/api/runs` 仍不显示 backup/archive 记录。
- [x] 页面能看到全局备份列表和诊断提示。
- [x] backup/archive 可以作为看板选项进入详情、结果图表和 artifact log 展示。

---

# 模块 12：本地源文件删除功能

## 概述

- 职责：为 dashboard 增加受控删除本地实验数据功能，删除真实源文件，而不是仅隐藏 UI 记录。
- 前置依赖：模块 11
- 预计步骤数：8
- 影响文件：
  - `dashboard/models.py`
  - `dashboard/delete_service.py`（新增）
  - `dashboard/api.py`
  - `dashboard/run_discovery.py`
  - `dashboard/state_store.py`
  - `monitor_dashboard.html`
  - `tests/test_delete_service.py`（新增）
  - `tests/test_api_delete.py`（新增）
  - `tests/test_frontend_delete_static.py`（新增或合并）
  - `docs/report.md`
  - `docs/progress.md`

## Step 1：新增删除领域模型

- **scope: auto**
- 文件：`dashboard/models.py`
- 操作：新增 dataclass：
  ```python
  @dataclass
  class DeleteTarget:
      target_id: str
      target_type: str
      display_name: str
      source_run_id: str = ""
      paths: list[str] = field(default_factory=list)
      exists: bool = True
      deletable: bool = True
      blocked_reason: str = ""
      warnings: list[str] = field(default_factory=list)

  @dataclass
  class DeletePreview:
      target_id: str
      target_type: str
      display_name: str
      paths: list[str]
      total_files: int
      total_dirs: int
      total_bytes: int
      blocked: bool
      blocked_reason: str = ""
      confirm_token: str = ""
      warnings: list[str] = field(default_factory=list)

  @dataclass
  class DeleteResult:
      target_id: str
      deleted_paths: list[str]
      skipped_paths: list[str] = field(default_factory=list)
      errors: list[str] = field(default_factory=list)
  ```
- `target_type` 允许：
  ```text
  active_run
  backup
  archive
  benchmark_export
  figure_archive
  ```
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.models import DeletePreview, dataclass_to_dict
  p = DeletePreview(target_id='x', target_type='backup', display_name='x', paths=['a'], total_files=1, total_dirs=0, total_bytes=10, blocked=False, confirm_token='abc')
  assert dataclass_to_dict(p)['confirm_token'] == 'abc'
  PY
  ```

## Step 2：新增删除服务与路径安全策略

- **scope: review**
- 文件：`dashboard/delete_service.py`
- 操作：新增类：
  ```python
  class LocalDataDeleteService:
      def __init__(self, config: DashboardConfig):
          ...

      def list_targets(self) -> list[DeleteTarget]:
          ...

      def preview_delete(self, target_id: str) -> DeletePreview:
          ...

      def confirm_delete(self, target_id: str, confirm_token: str) -> DeleteResult:
          ...
  ```
- 路径白名单：
  - `config.experiments_dir`
  - `config.logs_dir`
  - `config.runs_dir`
  - `config.results_dir`
  - `config.figures_dir`
  - `config.backup_scan_dirs`
- 安全规则：
  1. 所有待删路径必须 `resolve()` 后位于白名单根目录内。
  2. 禁止删除白名单根目录本身。
  3. 禁止删除路径名为 `.git`、`docs`、`dashboard`、`tests`、`scripts` 的目录。
  4. 禁止删除任意路径中包含 `.git` 片段。
  5. 删除 active run 时：
     - 若 `state.status in {"running", "stop_requested"}`，blocked。
     - 若 `process.json` 存在，blocked。
  6. 删除 backup/archive 可以删除：
     - backup experiment dir
     - matching `results/archive/<timestamp>`
     - matching `figures/archive/<timestamp>`
  7. 删除 benchmark export 可删除 `results/benchmark_<run_id>.json`。
  8. 用户反馈补充后，全局 `config.benchmark_json` 作为独立 `benchmark_json:latest` target，可在 preview/confirm 后删除。
- confirm token：
  - `preview_delete()` 生成 token：
    ```python
    sha256(f"{target_id}|{sorted(paths)}|{total_bytes}|dashboard-delete-v1")
    ```
  - `confirm_delete()` 必须重新 preview 并比对 token。
- 验证：
  ```bash
  python -m pytest tests/test_delete_service.py::test_delete_service_blocks_paths_outside_allowed_roots -v
  python -m pytest tests/test_delete_service.py::test_delete_service_blocks_running_experiment -v
  python -m pytest tests/test_delete_service.py::test_delete_service_deletes_backup_dir_and_matching_archives -v
  ```

## Step 3：实现删除 target discovery

- **scope: review**
- 文件：`dashboard/delete_service.py`
- 操作：
  - `list_targets()` 必须从当前 discovery 结果构造 target：
    1. active runs：来自 `discover_runs(config)` 中的 experiment descriptors
    2. backups：来自模块 11 的 backup discovery
    3. archive-only backups：来自 `discover_archive_only_backups(config.results_dir)`
    4. benchmark export：来自 run descriptor 的 `benchmark_export_file`
    5. structured runs：来自 `config.runs_dir`
    6. legacy logs：来自 `config.logs_dir`
    7. global benchmark JSON：来自 `config.benchmark_json`
- target_id 规则：
  ```text
  active_run:<run_id>
  backup:<backup_id>
  archive:<backup_id>
  benchmark_export:<run_id>
  structured_run:<run_id>
  legacy_log:<run_id>
  benchmark_json:latest
  ```
- 去重规则：
  - 同一物理路径只在一个 target 中出现；优先级：active_run > structured_run > legacy_log > backup > archive > benchmark_export > benchmark_json。
- 验证：
  ```bash
  python -m pytest tests/test_delete_service.py::test_list_targets_includes_active_run_backup_archive_and_benchmark_export -v
  python -m pytest tests/test_delete_service.py::test_list_targets_includes_legacy_logs_structured_runs_and_benchmark_json -v
  ```

## Step 4：新增删除 API

- **scope: review**
- 文件：`dashboard/api.py`
- 操作：新增 endpoint：
  ```python
  @app.get("/api/delete-targets")
  async def list_delete_targets():
      ...

  @app.post("/api/delete-preview")
  async def delete_preview(payload: dict):
      ...

  @app.post("/api/delete-confirm")
  async def delete_confirm(payload: dict):
      ...
  ```
- 请求/响应：
  - `POST /api/delete-preview`
    ```json
    {"target_id": "backup:paper2_full_17_vscode_backup_20260501_150000"}
    ```
    返回 `DeletePreview`
  - `POST /api/delete-confirm`
    ```json
    {
      "target_id": "backup:paper2_full_17_vscode_backup_20260501_150000",
      "confirm_token": "..."
    }
    ```
    返回 `DeleteResult`
- API 规则：
  - blocked preview 返回 200，`blocked=true`。
  - confirm blocked 返回 HTTP 409。
  - token 不匹配返回 HTTP 409。
  - 目标不存在返回 HTTP 404。
  - 删除完成后调用 `store.scan_all_once()` 刷新缓存。
- 验证：
  ```bash
  python -m pytest tests/test_api_delete.py::test_delete_preview_returns_confirm_token -v
  python -m pytest tests/test_api_delete.py::test_delete_confirm_removes_source_files_and_refreshes_runs -v
  python -m pytest tests/test_api_delete.py::test_delete_confirm_rejects_running_experiment -v
  python -m pytest tests/test_api_delete.py::test_delete_confirm_rejects_invalid_token -v
  python -m pytest tests/test_api_delete.py::test_delete_confirm_removes_legacy_log_source_files -v
  ```

## Step 5：前端新增 Danger Zone

- **scope: review**
- 文件：`monitor_dashboard.html`
- 操作：
  1. 新增 section：
     ```html
     <section class="panel danger-zone">
       <h2 data-i18n="delete.title">Danger Zone</h2>
       ...
     </section>
     ```
  2. 新增前端状态：
     ```js
     deleteTargets: [],
     pendingDeletePreview: null
     ```
  3. 新增函数：
     ```js
     async function loadDeleteTargets() { ... }
     async function previewDeleteTarget(targetId) { ... }
     async function confirmDeleteTarget() { ... }
     function renderDeleteTargets(targets) { ... }
     function renderDeletePreview(preview) { ... }
     ```
  4. UI 行为：
     - 每个 target 展示 target_type、display_name、paths 数量、blocked_reason。
     - 删除按钮文案必须包含“Delete Source Files”或中文“删除源文件”。
     - 点击删除先 preview。
     - preview 显示完整 paths、文件数、目录数、总大小。
     - confirm 要求用户输入目标 `target_id` 完全一致。
     - blocked target 禁用确认按钮。
- 禁止：
  - 不使用浏览器传入路径。
  - 不提供“delete all”。
  - 不自动删除。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_delete_static.py::test_frontend_contains_danger_zone_and_confirm_flow -v
  ```

## Step 6：删除后状态刷新与用户反馈

- **scope: auto**
- 文件：`monitor_dashboard.html`
- 操作：
  - `confirmDeleteTarget()` 成功后：
    1. 清空 `pendingDeletePreview`
    2. 调用 `loadRuns()`
    3. 调用 `loadBackups()`
    4. 调用 `loadDeleteTargets()`
    5. 若当前 selected run 被删除，自动选择剩余第一个 run；若无 run，清空详情区。
  - 错误时显示 `blocked_reason` 或 API detail。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_delete_static.py::test_frontend_refreshes_runs_backups_and_delete_targets_after_confirm -v
  ```

## Step 7：文档与启动说明更新

- **scope: auto**
- 文件：
  - `README.md`
  - `docs/windows-start-menu-launcher.md`（如存在）
- 操作：
  - 增加 `--backup-scan-dir` 说明。
  - 增加 `--figures-dir` 说明。
  - 增加删除功能说明：
    - 删除的是源文件。
    - 运行中实验不能删。
    - 删除前会 preview。
    - 删除后不可从 dashboard 恢复。
- 验证：
  ```bash
  python -m pytest tests/test_frontend_delete_static.py tests/test_config.py -v
  ```

## Step 8：全量回归与报告更新

- **scope: review**
- 文件：
  - `docs/plan.md`
  - `docs/progress.md`
  - `docs/report.md`
- 操作：
  - 更新 `docs/plan.md` Status：
    - 当前阶段：模块 11-12 完成，等待 review
    - 整体进度：62 / 62
    - 状态：NEEDS_REVIEW
  - 更新 `docs/progress.md`：
    - 新增模块 11、12 进度。
  - 更新 `docs/report.md`：
    - `STATUS: NEEDS_REVIEW`
    - 标记 `scope:review` 步骤待人工确认。
- 全量验证：
  ```bash
  python -m pytest tests/test_run_discovery_experiments.py tests/test_api_experiments.py tests/test_delete_service.py tests/test_api_delete.py -v
  python -m pytest -v
  ```
- 手动验证：
  1. 启动 dashboard。
  2. 当前训练 run 仍显示。
  3. `/api/backups/diagnostics` 显示扫描目录。
  4. VSCode Backup Full 17 Data 产物显示在 Backups 面板。
  5. 删除非运行中 backup，源目录确实消失。
  6. 删除运行中 active run 被拒绝。
  7. 删除后 `/api/runs`、`/api/backups` 自动刷新。

## 模块 12 验收标准

- [x] `/api/delete-targets` 只返回安全白名单内目标。
- [x] `/api/delete-preview` 不删除文件，只返回 preview 与 confirm token。
- [x] `/api/delete-confirm` token 不匹配时拒绝。
- [x] 运行中实验和存在 `process.json` 的实验无法删除。
- [x] 删除 backup 会删除真实 backup experiment dir 与匹配 archive。
- [x] 删除 archive-only 只删除 archive 目录，不影响 active run。
- [x] 删除 benchmark export 可删除 `results/benchmark_<run_id>.json`。
- [x] 全局 `results/benchmark.json` 作为独立 target，经 preview/confirm 后可删除。
- [x] 删除 legacy log / structured run 源文件经 preview/confirm 后可执行。
- [x] 前端 Danger Zone 要求二次确认并显示完整 paths。
- [x] 全量测试通过。

---

## Codex 执行注意事项

1. 只执行模块 11 和模块 12。
2. 模块 1-10 不重做；必要时允许最小兼容改动。
3. 所有新增 destructive API 必须有测试。
4. 不要让前端传任意路径给后端删除。
5. 不要删除运行中实验。
6. 不要提供一键全部删除。
7. 删除完成后必须刷新 state store。
8. 执行完成后 `docs/report.md` 仍保持 `NEEDS_REVIEW`，等待人工确认。
