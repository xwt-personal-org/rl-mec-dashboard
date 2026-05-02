# 开发计划：rl-mec-dashboard 对齐 paper2 新实验编排架构

## 元信息

- 项目：`rl-mec-dashboard`
- 仓库：`w2030298-art/rl-mec-dashboard`
- 计划类型：已有项目迁移改造计划
- 路线判定：简单路线；这是一次明确的数据契约迁移与 UI/后端适配，不涉及新算法、论文调研或模型实现，因此跳过技术调研与独立架构设计，直接进入计划制定。
- 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。
- 当前架构基线：后端已模块化为 `dashboard/` 包，现有 reader/discovery/aggregator 仍主要服务于 legacy logs 与旧 structured runs 协议。
- 新 paper2 数据源：`experiments/<run_id>/run.json`、`experiments/<run_id>/state.json`、`experiments/<run_id>/process.json`、`experiments/<run_id>/artifacts/<ALGORITHM>/{stdout.log,stderr.log,result.json}`、`results/benchmark_<run_id>.json`。
- 总模块数：9
- 预计步骤总数：42
- 建议开发顺序：配置与模型 → 新实验读取器 → 发现与聚合 → API → 前端 UI → benchmark 图表兼容 → 测试 fixtures → 文档脚本 → 全量验收

## 关键迁移原则

1. `experiments/<run_id>/state.json` 是实时状态唯一真实来源；不能再用 `results/benchmark.json` 或旧日志推断当前实验状态。
2. `run.json.algorithms` 决定算法表格顺序；不能从目录名或 result 文件猜测顺序。
3. 训练失败定位到具体算法：`records[].status` + `records[].error` + `artifacts/<ALGORITHM>/stdout.log` / `stderr.log`。
4. `stderr.log` 非空不代表失败；失败只由 `record.status` 决定。
5. `record.status == "running"` 时，必须忽略旧的 `error`、`exit_code`、`finished_at` 残留字段。
6. `results/benchmark_<run_id>.json` 仅用于兼容旧图表和聚合结果，不用于判断当前实验状态。
7. 本轮 dashboard 仍保持只读；不实现训练调度后端，不 kill 训练进程，不删除 `experiments/`。
8. 保留 legacy fallback，但新 paper2 `experiments/` 协议优先级最高。

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

### Step 1：扩展 `DashboardConfig`

- 操作：修改 `dashboard/config.py` 中的 `DashboardConfig` dataclass，新增字段：
  - `experiments_dir: Path | None`
  - `results_dir: Path`
  - `default_run_id: str`
  - `quick_run_id: str`
  - `log_tail_bytes: int`
  - `json_retry_keep_last: bool`
- 保留字段：
  - `logs_dir: Path`
  - `benchmark_json: Path`
  - `runs_dir: Path | None`
  - `host: str`
  - `port: int`
  - `scan_interval_sec: float`
  - `stall_threshold_sec: int`
  - `recent_log_limit: int`
  - `sse_interval_sec: float`
- 默认值要求：
  - `experiments_dir=Path("experiments")`
  - `results_dir=Path("results")`
  - `benchmark_json=Path("results/benchmark.json")`
  - `default_run_id="paper2_full_17_vscode"`
  - `quick_run_id="vscode_quick"`
  - `log_tail_bytes=65536`
  - `json_retry_keep_last=True`
- 验证：运行 `python -c "from dashboard.config import create_default_config; c=create_default_config(); assert c.experiments_dir.name == 'experiments'; assert c.default_run_id == 'paper2_full_17_vscode'"`

### Step 2：更新 CLI 参数解析

- 操作：修改 `dashboard/config.py` 的 `parse_cli_args(argv)`：
  - 新增 `--experiments-dir`，默认 `experiments`。
  - 新增 `--results-dir`，默认 `results`。
  - 新增 `--default-run-id`，默认 `paper2_full_17_vscode`。
  - 新增 `--quick-run-id`，默认 `vscode_quick`。
  - 新增 `--log-tail-bytes`，默认 `65536`。
  - 保留 `--runs-dir`，但标注为 legacy/deprecated。
  - 当用户只传 `--runs-dir` 而未显式传 `--experiments-dir` 时，不把 `runs_dir` 当作新实验目录；`runs_dir` 仅继续用于旧 structured runs fallback。
- 验证：运行：
  ```bash
  python - <<'PY'
  from dashboard.config import parse_cli_args
  c = parse_cli_args(['--experiments-dir','C:/paper2/experiments','--results-dir','C:/paper2/results'])
  assert str(c.experiments_dir).endswith('experiments')
  assert str(c.results_dir).endswith('results')
  assert c.runs_dir is None
  PY
  ```

### Step 3：更新 `serve_dashboard.py`

- 操作：检查并修改 `serve_dashboard.py`：
  - 必须继续只调用 `parse_cli_args()` 和 `create_app(config)`。
  - 不在 `serve_dashboard.py` 中写任何路径拼接逻辑。
  - 启动日志打印 `experiments_dir`、`results_dir`、`logs_dir`、`benchmark_json`。
- 验证：运行 `python serve_dashboard.py --help`，输出中包含 `--experiments-dir`、`--results-dir`、`--log-tail-bytes`。

### Step 4：定义固定结果路径 helper

- 操作：在 `dashboard/config.py` 新增函数：
  - `benchmark_export_path(config: DashboardConfig, run_id: str) -> Path`
- 实现要求：
  - 返回 `config.results_dir / f"benchmark_{run_id}.json"`。
  - 不返回 `benchmark.json` alias。
- 验证：运行：
  ```bash
  python - <<'PY'
  from dashboard.config import create_default_config, benchmark_export_path
  c = create_default_config()
  assert str(benchmark_export_path(c, 'paper2_full_17_vscode')).replace('\\\\','/').endswith('results/benchmark_paper2_full_17_vscode.json')
  PY
  ```

### Step 5：添加配置测试

- 操作：新增 `tests/test_config.py`，覆盖：
  - `test_default_config_uses_experiments_dir`
  - `test_parse_cli_experiments_and_results_dir`
  - `test_legacy_runs_dir_does_not_override_experiments_dir`
  - `test_benchmark_export_path`
- 验证：运行 `python -m pytest tests/test_config.py -v` 全部通过。

### 验收标准

- [ ] 新 CLI 参数存在且默认值正确。
- [ ] 旧 `--runs-dir` 仍可用，但只服务 legacy structured runs。
- [ ] 所有路径 helper 不写死 Windows 绝对路径。

---

## 模块 2：领域模型对齐 paper2 实验状态机

### 概述

- 职责：把后端内部 DTO 从旧 run/progress 模型扩展为 experiment/state/algorithm record 模型，并兼容旧 API 字段。
- 前置依赖：模块 1
- 预计步骤数：5

### Step 1：扩展状态枚举

- 操作：修改 `dashboard/models.py`，新增 Literal 类型：
  - `ExperimentStatus = Literal["initialized", "running", "stop_requested", "stopped", "completed", "failed"]`
  - `AlgorithmStatus = Literal["pending", "running", "completed", "interrupted", "failed", "skipped"]`
  - `SourceType = Literal["experiment_state", "legacy_structured", "legacy_log", "mixed", "placeholder"]`
- 保留旧 `RunStatus`，但允许兼容新状态：
  - 修改为 `Literal["idle", "running", "finished", "stalled", "degraded", "failed", "initialized", "stop_requested", "stopped", "completed"]`
- 验证：运行 `python -c "from dashboard.models import ExperimentStatus, AlgorithmStatus"` 无报错。

### Step 2：新增算法记录模型

- 操作：在 `dashboard/models.py` 新增 dataclass：
  - `AlgorithmRunRecord`
- 字段必须包含：
  - `name: str`
  - `status: str = "pending"`
  - `attempts: int = 0`
  - `started_at: str | None = None`
  - `finished_at: str | None = None`
  - `exit_code: int | None = None`
  - `device: str = ""`
  - `result_path: str = ""`
  - `checkpoint_dir: str = ""`
  - `stdout_path: str = ""`
  - `stderr_path: str = ""`
  - `error: str | None = None`
  - `result_missing: bool = False`
- 错误字段规则：
  - 当原始 `record.status not in {"failed", "interrupted"}` 时，`error` 必须设为 `None`。
  - 当 `record.status == "running"` 时，即使原始 state 中存在 `error`，也必须设为 `None`。
- 验证：运行 `python -c "from dashboard.models import AlgorithmRunRecord; r=AlgorithmRunRecord(name='GRPO'); assert r.status == 'pending'"`。

### Step 3：新增实验清单与实验状态模型

- 操作：在 `dashboard/models.py` 新增：
  - `AlgorithmSpec`
  - `ExperimentRunManifest`
  - `ExperimentStateSnapshot`
- `AlgorithmSpec` 字段：
  - `name: str`
  - `config_path: str = ""`
  - `timesteps: int | None = None`
  - `seed: int | None = None`
  - `device: str = ""`
  - `env: str = ""`
  - `eval_episodes: int | None = None`
  - `extra_args: list[str] = field(default_factory=list)`
- `ExperimentRunManifest` 字段：
  - `schema_version: int`
  - `run_id: str`
  - `name: str`
  - `created_at: str`
  - `updated_at: str`
  - `algorithms: list[AlgorithmSpec]`
  - `project_root: str`
  - `output_dir: str`
  - `experiment_dir: str`
  - `metadata: dict[str, Any]`
- `ExperimentStateSnapshot` 字段：
  - `schema_version: int`
  - `run_id: str`
  - `status: str`
  - `current_index: int`
  - `records: list[AlgorithmRunRecord]`
  - `completed_algorithms: list[str]`
  - `stop_requested: bool`
  - `last_error: str | None`
  - `updated_at: str`
- 验证：运行 `python -c "from dashboard.models import ExperimentRunManifest, ExperimentStateSnapshot"`。

### Step 4：扩展 `AlgorithmResult`

- 操作：修改 `dashboard/models.py` 中的 `AlgorithmResult`，新增字段：
  - `seed: int | None = None`
  - `device: str = ""`
  - `train_timesteps: int | None = None`
  - `checkpoint_dir: str = ""`
  - `result_path: str = ""`
  - `final_eval: dict[str, Any] = field(default_factory=dict)`
- 保留旧字段：`reward`、`reward_std`、`latency`、`energy`、`comm_score`、`train_time`、`update_count` 等。
- 验证：运行：
  ```bash
  python - <<'PY'
  from dashboard.models import AlgorithmResult, algorithm_result_to_dict
  r = AlgorithmResult(algorithm='GRPO', seed=42, final_eval={'eval/reward_mean': 1.0})
  d = algorithm_result_to_dict(r)
  assert d['seed'] == 42
  assert d['final_eval']['eval/reward_mean'] == 1.0
  PY
  ```

### Step 5：扩展 `RunState`

- 操作：修改 `dashboard/models.py` 中的 `RunState`，新增字段：
  - `display_name: str = ""`
  - `records: list[AlgorithmRunRecord | dict[str, Any]] = field(default_factory=list)`
  - `current_index: int = 0`
  - `stop_requested: bool = False`
  - `run_manifest_path: str = ""`
  - `state_path: str = ""`
  - `process_path: str = ""`
  - `benchmark_export_path: str = ""`
  - `process_marker_exists: bool = False`
  - `possibly_stale: bool = False`
  - `schema_version: int = 1`
- 兼容要求：
  - 不删除旧字段 `current_algorithm`、`progress_pct`、`overall_progress`、`results`、`recent_logs`。
  - 前端可以逐步从旧字段迁移到 `records`。
- 验证：运行 `python -c "from dashboard.models import RunState; s=RunState(run_id='x'); assert isinstance(s.records, list)"`。

### 验收标准

- [ ] 新状态模型可表达 `run.json`、`state.json` 和每算法记录。
- [ ] 旧 API 序列化函数 `dataclass_to_dict()` 不报错。
- [ ] 旧字段不删除，避免一次性破坏前端。

---

## 模块 3：新增 paper2 实验文件读取器

### 概述

- 职责：以只读、容错方式读取 `experiments/<run_id>/` 下的 `run.json`、`state.json`、`process.json`、artifact logs、单算法 `result.json`。
- 前置依赖：模块 2
- 预计步骤数：7

### Step 1：创建 `dashboard/experiment_reader.py`

- 操作：新增文件 `dashboard/experiment_reader.py`。
- 文件内必须定义：
  - `safe_read_json_file(path: Path) -> tuple[dict[str, Any] | list[Any] | None, str | None]`
  - `read_text_tail(path: Path, max_bytes: int = 65536) -> tuple[str, bool]`
  - `Paper2ExperimentReader`
- 验证：运行 `python -c "from dashboard.experiment_reader import Paper2ExperimentReader, safe_read_json_file, read_text_tail"`。

### Step 2：实现原子写容错读取

- 操作：在 `safe_read_json_file(path)` 中实现：
  - 文件不存在返回 `(None, None)`。
  - 空文件返回 `(None, "empty json file: <path>")`。
  - JSON 解析失败返回 `(None, "invalid json file: <path>")`，不抛异常。
  - 其他读取异常返回 `(None, str(exc))`，不抛异常。
- 验证：新增 `tests/test_experiment_reader.py::test_safe_read_json_file_handles_missing_empty_invalid`。

### Step 3：实现日志尾部读取

- 操作：在 `read_text_tail(path, max_bytes)` 中实现：
  - 文件不存在返回 `("", False)`。
  - 大文件只读取最后 `max_bytes` 字节。
  - 使用 `encoding="utf-8", errors="replace"`。
  - 不执行日志内容，不做 HTML 注入。
- 验证：新增 `tests/test_experiment_reader.py::test_read_text_tail_limits_large_log`。

### Step 4：实现 `Paper2ExperimentReader.__init__`

- 操作：实现类：
  ```python
  class Paper2ExperimentReader:
      def __init__(self, experiment_dir: Path):
          self.experiment_dir = Path(experiment_dir)
          self.run_json_path = self.experiment_dir / "run.json"
          self.state_json_path = self.experiment_dir / "state.json"
          self.process_json_path = self.experiment_dir / "process.json"
          self.artifacts_dir = self.experiment_dir / "artifacts"
  ```
- 新增方法：
  - `exists(self) -> bool`：`run.json` 或 `state.json` 任一存在即返回 True。
  - `artifact_base(self, algorithm: str) -> Path`：返回 `artifacts/<ALGORITHM>`。
  - `stdout_path(self, algorithm: str) -> Path`
  - `stderr_path(self, algorithm: str) -> Path`
  - `default_result_path(self, algorithm: str) -> Path`
- 验证：新增 `tests/test_experiment_reader.py::test_reader_paths`。

### Step 5：实现 `read_run_manifest()`

- 操作：在 `Paper2ExperimentReader` 中新增方法：
  - `read_run_manifest(self) -> tuple[ExperimentRunManifest | None, str | None]`
- 映射规则：
  - `schema_version` 默认 `1`。
  - `algorithms` 从 `payload["algorithms"]` 读取，按原顺序转换为 `AlgorithmSpec`。
  - 缺失 `name` 的算法条目跳过。
  - `name` 字段缺失时使用 `run_id`。
- 验证：新增 `tests/test_experiment_reader.py::test_read_run_manifest_preserves_algorithm_order`。

### Step 6：实现 `read_state_snapshot()`

- 操作：在 `Paper2ExperimentReader` 中新增方法：
  - `read_state_snapshot(self, manifest: ExperimentRunManifest | None = None) -> tuple[ExperimentStateSnapshot | None, str | None]`
- 映射规则：
  - `records[]` 按 `state.json.records` 顺序读取。
  - 若 `records[]` 为空但 `manifest.algorithms` 存在，则为每个算法生成 `pending` 记录。
  - 每个 record 的 `stdout_path` 固定为 `experiments/<run_id>/artifacts/<ALGORITHM>/stdout.log`。
  - 每个 record 的 `stderr_path` 固定为 `experiments/<run_id>/artifacts/<ALGORITHM>/stderr.log`。
  - `result_path` 优先使用 `record.result_path`，否则使用固定路径 `artifacts/<ALGORITHM>/result.json`。
  - `error` 只在 `status in {"failed", "interrupted"}` 时保留，其余状态设为 `None`。
- 验证：新增：
  - `tests/test_experiment_reader.py::test_read_state_snapshot_generates_paths`
  - `tests/test_experiment_reader.py::test_running_record_ignores_stale_error`

### Step 7：实现 `read_algorithm_result()`

- 操作：在 `Paper2ExperimentReader` 中新增方法：
  - `read_algorithm_result(self, record: AlgorithmRunRecord) -> tuple[AlgorithmResult | None, str | None]`
- 读取规则：
  - 只有 `record.status == "completed"` 时读取。
  - `record.result_path` 为空时读 `default_result_path(record.name)`。
  - 文件缺失返回 `(None, "result file missing: <path>")`。
  - `payload["final_eval"]` 中常见 key 映射：
    - `eval/reward_mean` → `AlgorithmResult.reward`
    - `eval/reward_std` → `AlgorithmResult.reward_std`
    - `eval/latency_mean` → `AlgorithmResult.latency`
    - `eval/energy_mean` → `AlgorithmResult.energy`
    - `eval/comm_score` → `AlgorithmResult.comm_score`
  - 同时保留完整 `final_eval` 原始字典。
  - 字段 `algorithm`、`environment`、`seed`、`device`、`train_timesteps`、`checkpoint_dir` 从 payload 中读取。
  - `AlgorithmResult.status` 设置为 `"finished"`，`source` 设置为 `"structured"`。
- 验证：新增：
  - `tests/test_experiment_reader.py::test_read_algorithm_result_maps_final_eval`
  - `tests/test_experiment_reader.py::test_completed_record_missing_result_is_reported`

### 验收标准

- [ ] 新 reader 不依赖旧 `events.jsonl` / `summary.json`。
- [ ] JSON 解析失败不会导致整个 dashboard 500。
- [ ] `running` 记录中的旧错误不会展示为当前失败。
- [ ] `result.json` 缺失时可被准确标记。

---

## 模块 4：实验发现与状态聚合改造

### 概述

- 职责：让 dashboard 优先发现 `experiments/<run_id>/`，并基于 `state.json` 合成 `RunSummary` 与 `RunState`。
- 前置依赖：模块 1、2、3
- 预计步骤数：7

### Step 1：扩展 `RunDescriptor`

- 操作：修改 `dashboard/models.py` 中的 `RunDescriptor`，新增字段：
  - `experiment_dir: Path | None = None`
  - `run_json_file: Path | None = None`
  - `state_json_file: Path | None = None`
  - `process_json_file: Path | None = None`
  - `benchmark_export_file: Path | None = None`
  - `is_placeholder: bool = False`
- `source_type` 新增使用 `"experiment_state"`。
- 验证：运行 `python -c "from dashboard.models import RunDescriptor; d=RunDescriptor(run_id='x', source_type='experiment_state'); assert d.source_type == 'experiment_state'"`。

### Step 2：实现 `discover_experiment_runs()`

- 操作：修改 `dashboard/run_discovery.py`，新增函数：
  - `discover_experiment_runs(experiments_dir: Path | None, results_dir: Path) -> list[RunDescriptor]`
- 发现规则：
  - `experiments_dir is None` 或目录不存在时返回空列表。
  - 遍历 `experiments_dir.iterdir()`，只接受目录。
  - 目录内存在 `run.json` 或 `state.json` 时生成 descriptor。
  - `run_id` 优先从 `run.json.run_id` 读取，其次用目录名。
  - `mtime` 取 `run.json`、`state.json`、`process.json` 中存在文件的最大 `st_mtime`。
  - `benchmark_export_file = results_dir / f"benchmark_{run_id}.json"`。
- 验证：新增 `tests/test_run_discovery_experiments.py::test_discover_experiment_runs_finds_state_json`。

### Step 3：保留默认入口 placeholder

- 操作：在 `dashboard/run_discovery.py` 新增函数：
  - `default_experiment_placeholders(config: DashboardConfig) -> list[RunDescriptor]`
- 规则：
  - 始终为 `config.default_run_id` 和 `config.quick_run_id` 创建 descriptor。
  - 若真实 experiment descriptor 已存在，则不添加 placeholder。
  - placeholder 的 `source_type="placeholder"`，`is_placeholder=True`，`display_name` 分别为：
    - `Paper2 Full 17 Algorithms VSCode Benchmark`
    - `VSCode Quick Benchmark`
- 验证：新增 `tests/test_run_discovery_experiments.py::test_default_placeholders_are_added_when_files_missing`。

### Step 4：更新 `discover_runs(config)` 优先级

- 操作：修改 `dashboard/run_discovery.py` 中的 `discover_runs(config)`：
  - 第一优先级：`discover_experiment_runs(config.experiments_dir, config.results_dir)`。
  - 第二优先级：旧 `discover_structured_runs(config.runs_dir)`，source type 改为 `legacy_structured`。
  - 第三优先级：`discover_legacy_runs(config.logs_dir)`。
  - 最后补充 default placeholders。
  - 同名 run 合并时优先保留 `experiment_state`。
- 禁止：不要读取 `experiments/.index.sqlite3`。
- 验证：新增 `tests/test_run_discovery_experiments.py::test_experiment_descriptor_wins_over_legacy_same_run_id`。

### Step 5：实现 `RunStateAggregator.scan_experiment_once()`

- 操作：修改 `dashboard/state_aggregator.py`，新增方法：
  - `scan_experiment_once(self, descriptor: RunDescriptor, state: RunState) -> RunState`
- 合成规则：
  - 用 `Paper2ExperimentReader` 读取 manifest、state snapshot、process marker。
  - `RunState.run_id = snapshot.run_id or manifest.run_id or descriptor.run_id`。
  - `RunState.display_name = manifest.name or descriptor.display_name or run_id`。
  - `RunState.status = snapshot.status`。
  - `RunState.records = snapshot.records`。
  - `RunState.completed_algorithms = snapshot.completed_algorithms`。
  - `RunState.total_algorithms = len(snapshot.records)`。
  - `RunState.current_index = snapshot.current_index`。
  - `RunState.current_algorithm = records[current_index].name`；越界时取第一个 `status != "completed"` 的记录；仍无则为 `""`。
  - `RunState.progress_pct = completed / total * 100`，total 为 0 时为 0。
  - `RunState.overall_progress = completed`。
  - `RunState.last_error = snapshot.last_error`，但 algorithm 级旧 error 仍由 record 规则控制。
  - `RunState.process_marker_exists = process.json.exists()`。
  - `RunState.possibly_stale = process_marker_exists and status == "running" and state.updated_at 超过 stall_threshold_sec 且日志大小不增长`；第一版可只用 `updated_at` 时间差判断。
  - `RunState.run_manifest_path`、`state_path`、`process_path`、`benchmark_export_path` 填充为字符串路径。
- 验证：新增 `tests/test_state_aggregator_experiments.py::test_scan_experiment_once_builds_run_state_from_state_json`。

### Step 6：读取 completed 算法 `result.json`

- 操作：在 `scan_experiment_once()` 中遍历 `state.records`：
  - 对 `status == "completed"` 的记录调用 `reader.read_algorithm_result(record)`。
  - 成功结果加入 `RunState.results`。
  - 缺失结果文件时：
    - 该 record 的 `result_missing=True`。
    - 在 `recent_logs` 中追加 warn：`Result file missing for <ALGORITHM>: <path>`。
    - 不把算法从 completed 改成 failed；UI 显示“结果文件缺失”。
- 验证：新增 `tests/test_state_aggregator_experiments.py::test_completed_missing_result_sets_result_missing_warning`。

### Step 7：更新 `scan_once()` 分派逻辑

- 操作：修改 `dashboard/state_aggregator.py` 的 `scan_once()`：
  - 当 `descriptor.source_type in {"experiment_state", "placeholder"}` 时调用 `scan_experiment_once()`。
  - 否则保留旧 structured/log 逻辑。
  - `placeholder` 生成 `RunState`：
    - `status="initialized"`
    - `records=[]`
    - `current_algorithm=""`
    - `progress_pct=0`
    - `display_name=descriptor.display_name`
- 验证：运行：
  ```bash
  python -m pytest tests/test_state_aggregator_experiments.py tests/test_run_discovery_experiments.py -v
  ```

### 验收标准

- [ ] `/api/runs` 优先显示 `experiments/` 中的 run。
- [ ] Full 17 与 Quick 即使文件未生成，也可作为入口卡片显示为“等待生成”。
- [ ] `state.json` 中 `records` 是算法表格唯一状态来源。
- [ ] 旧 legacy logs 仍可在没有新 experiments 时工作。

---

## 模块 5：API 层适配新实验视图与日志读取

### 概述

- 职责：在现有 FastAPI API 上暴露新实验状态、日志 tail、benchmark export，并保持原 `/api/runs`、`/api/runs/{run_id}` 不破坏。
- 前置依赖：模块 4
- 预计步骤数：6

### Step 1：扩展 `/api/health`

- 操作：修改 `dashboard/api.py` 中的 `/api/health` 返回：
  - `version: "0.3.0"`
  - `has_experiment_state: bool`
  - `has_structured_protocol: bool` 保留兼容。
  - `run_count: int`
  - `default_run_id: str`
  - `quick_run_id: str`
- 验证：新增 `tests/test_api_experiments.py::test_health_reports_experiment_state_support`。

### Step 2：保持 `/api/runs` 返回列表并增加默认入口信息

- 操作：修改 `/api/runs`：
  - 继续返回 `{ "runs": [...] }`。
  - 每个 run summary 必须包含：
    - `run_id`
    - `display_name`
    - `status`
    - `current_algorithm`
    - `progress_pct`
    - `total_algorithms`
    - `source_type`
    - `has_error`
    - `last_error`
    - `is_placeholder`
- 实现：需要修改 `RunSummary` dataclass，新增 `is_placeholder: bool = False`，并在 `_summary_from_state()` 中填充。
- 验证：新增 `tests/test_api_experiments.py::test_list_runs_contains_full17_and_quick_placeholders`。

### Step 3：扩展 `/api/runs/{run_id}` 详情

- 操作：保持现有 endpoint 名称，返回 `run_state_to_dict(state)`。
- 必须包含字段：
  - `records[]`，每个 record 包含 `stdout_path`、`stderr_path`、`result_path`、`result_missing`。
  - `results[]`，completed 算法已有 result 时包含映射指标和 `final_eval`。
  - `benchmark_export_path`。
  - `process_marker_exists`。
  - `possibly_stale`。
- 验证：新增 `tests/test_api_experiments.py::test_get_run_detail_contains_records_and_artifact_paths`。

### Step 4：新增日志 tail API

- 操作：在 `dashboard/api.py` 新增：
  - `GET /api/runs/{run_id}/logs/{algorithm}/stdout`
  - `GET /api/runs/{run_id}/logs/{algorithm}/stderr`
- 实现规则：
  - 从当前 run state 的 `records` 中查找 algorithm。
  - stdout endpoint 读取 `record.stdout_path`。
  - stderr endpoint 读取 `record.stderr_path`。
  - 使用 `read_text_tail(path, store.config.log_tail_bytes)`。
  - 返回 JSON：
    ```json
    {"run_id":"...", "algorithm":"GRPO", "stream":"stdout", "path":"...", "exists":true, "text":"..."}
    ```
  - 文件不存在不报 404，返回 `exists=false` 和 `text=""`。
  - algorithm 不存在时返回 404。
- 验证：新增：
  - `tests/test_api_experiments.py::test_stdout_log_endpoint_returns_tail`
  - `tests/test_api_experiments.py::test_missing_log_endpoint_returns_exists_false`

### Step 5：新增 benchmark export API

- 操作：在 `dashboard/api.py` 新增：
  - `GET /api/runs/{run_id}/benchmark`
- 实现规则：
  - 读取 `results/benchmark_<run_id>.json`。
  - 文件不存在时返回 `{ "run_id": run_id, "exists": false, "results": [] }`。
  - 文件存在且为数组时返回 `{ "run_id": run_id, "exists": true, "results": payload }`。
  - JSON 解析失败时返回 HTTP 200 + `{ "exists": true, "transient_error": "invalid json file: ...", "results": [] }`，前端下一轮重试。
  - 空数组 `[]` 是合法状态，不作为加载失败。
- 验证：新增：
  - `tests/test_api_experiments.py::test_benchmark_export_empty_array_is_valid`
  - `tests/test_api_experiments.py::test_missing_benchmark_export_is_not_500`

### Step 6：SSE 继续推送 run snapshot

- 操作：检查 `dashboard/sse.py`：
  - 确认 `/api/runs/{run_id}/events` 推送的是新 `RunState` 字典。
  - SSE 不单独推送日志全量文本，避免大日志持续刷屏。
  - 前端日志通过 Step 4 的 tail API 轮询。
- 验证：新增或更新 `tests/test_api_experiments.py::test_sse_endpoint_exists_for_experiment_run`；若当前测试框架不方便消费 streaming response，只断言 endpoint 对有效 run 不返回 404。

### 验收标准

- [ ] 所有新增 API 只读。
- [ ] 旧 `/api/runs`、`/api/runs/{run_id}` 路径不改名。
- [ ] 日志 API 对不存在文件容错。
- [ ] benchmark 空数组不被视作错误。

---

## 模块 6：前端 `monitor_dashboard.html` 迁移

### 概述

- 职责：让单文件前端显示新实验入口、算法状态表、日志定位、结果指标和 benchmark 图表。
- 前置依赖：模块 5
- 预计步骤数：6

### Step 1：更新前端数据模型常量

- 操作：修改 `monitor_dashboard.html` 中的 JavaScript：
  - 新增常量：
    ```js
    const DEFAULT_RUN_ID = 'paper2_full_17_vscode';
    const QUICK_RUN_ID = 'vscode_quick';
    const EXPERIMENT_STATUSES = ['initialized','running','stop_requested','stopped','completed','failed'];
    const ALGORITHM_STATUSES = ['pending','running','completed','interrupted','failed','skipped'];
    ```
  - 保留旧字段解析函数，但新渲染优先用 `records`。
- 验证：启动页面后浏览器控制台无 `ReferenceError`。

### Step 2：首页增加固定入口卡片

- 操作：在 `monitor_dashboard.html` 中修改 run list 渲染：
  - Full 17 卡片固定优先显示，run id `paper2_full_17_vscode`。
  - Quick 卡片固定显示为诊断入口，run id `vscode_quick`。
  - Quick 卡片文案必须明确：`Quick smoke test，仅用于入口连通性和失败定位，不作为正式论文结果`。
  - 其他历史 runs 按更新时间排序显示在下方。
- 验证：用 API 只返回 placeholder 时，页面仍显示 Full 17 与 Quick 两张卡片。

### Step 3：实现算法状态表

- 操作：新增或替换算法表渲染函数：
  - 函数名建议：`renderAlgorithmTable(runState)`。
  - 表格列：`#`、`Algorithm`、`Status`、`Attempts`、`Device`、`Started`、`Finished`、`Result`、`Logs`、`Error`。
  - 行顺序使用 `runState.records`，后端已按 `run.json.algorithms` 排好。
  - 当前算法高亮：`index === runState.current_index`；若越界则高亮第一条 `status !== 'completed'`。
  - `record.status === 'running'` 时忽略 `record.error`。
  - `record.status in ['failed','interrupted']` 时显示错误摘要。
  - `record.result_missing === true` 时 Result 列显示 `结果文件缺失`。
- 验证：用 fixture API 返回 Quick failed state 时，GRPO 行显示 failed，PPO/SAC 显示 pending。

### Step 4：实现 stdout/stderr 日志面板

- 操作：新增函数：
  - `loadAlgorithmLog(runId, algorithm, stream)`
  - `renderLogPanel(runState, selectedAlgorithm)`
- 交互规则：
  - 点击表格 Logs 中的 `stdout` / `stderr` 按钮后调用对应 API。
  - 当算法 `status === 'failed'` 时默认打开 `stderr` tab。
  - `stderr` 非空但算法未失败时，不显示红色失败状态，只显示普通日志。
  - 日志内容使用 `textContent` 渲染，不用 `innerHTML`。
  - 对 `\r` 回车进度条，第一版处理为 `text.replace(/\r/g, '\n')`。
- 验证：打开含 `<script>` 文本的日志 fixture，页面不执行脚本，仅显示文本。

### Step 5：实现实验进度与 stale marker 展示

- 操作：更新 run detail header：
  - 进度显示：`completed_algorithms.length / records.length`。
  - 状态 badge 使用 `runState.status`。
  - `process_marker_exists && status === 'running'` 显示 `process marker present`。
  - `possibly_stale === true` 显示 `可能卡住 / 需人工确认`。
  - `state.status === 'completed'` 停止自动轮询。
  - `state.status === 'failed' || state.status === 'stopped'` 降低轮询频率或停止状态轮询，保留手动刷新按钮。
- 验证：模拟 completed state 后前端不再继续每 2 秒轮询状态。

### Step 6：更新结果与图表渲染

- 操作：前端结果页逻辑改为：
  - 实时详情页优先展示 `runState.results[]`。
  - 图表页点击刷新时调用 `/api/runs/{runId}/benchmark`。
  - benchmark 结果为空数组时显示 `暂无已完成算法结果`。
  - 指标 key 容错：缺失显示 `N/A`。
  - 常见指标：Reward、Latency、Energy、Comm Score。
- 验证：用 `/api/runs/{run_id}/benchmark` 返回 `{exists:true, results:[]}`，页面显示“暂无已完成算法结果”，不显示加载错误。

### 验收标准

- [ ] 页面不再依赖单个 `results/benchmark.json` 判断训练状态。
- [ ] Full 17/Quick 默认入口可见。
- [ ] 失败算法可直接打开 stdout/stderr。
- [ ] 旧 error 残留不会污染 running 状态。
- [ ] benchmark 空数组显示为空状态而非报错。

---

## 模块 7：benchmark 兼容与导出映射

### 概述

- 职责：兼容新 `results/benchmark_<run_id>.json` 字段，同时保留现有 compare/export 能力。
- 前置依赖：模块 5、6
- 预计步骤数：3

### Step 1：更新 benchmark loader 字段映射

- 操作：修改 `dashboard/run_discovery.py` 中 `load_benchmark_results(json_path)`：
  - 支持旧字段：
    - `final_reward_mean_mean`
    - `final_reward_mean_std`
    - `train_time_seconds_mean`
    - `final_latency_mean_mean`
    - `final_energy_mean_mean`
    - `final_comm_score_mean`
  - 支持新字段：
    - `final_reward_mean`
    - `final_reward_std`
    - `final_latency_mean`
    - `final_energy_mean`
    - `final_comm_score`
    - `train_timesteps`
    - `checkpoint_dir`
    - `seed`
    - `device`
    - `status`
  - 新字段优先于旧字段。
- 验证：新增 `tests/test_benchmark_loader.py::test_load_new_benchmark_export_fields`。

### Step 2：状态聚合中按 run_id 读取 benchmark export

- 操作：在 `RunStateAggregator.scan_experiment_once()` 中：
  - 使用 descriptor 的 `benchmark_export_file` 加载 fallback benchmark results。
  - 不使用 `results/benchmark.json` 判断状态。
  - fallback 只补充 `RunState.results` 中缺失的指标，不覆盖 per-algorithm `result.json` 的 `structured` 结果。
- 验证：新增 `tests/test_state_aggregator_experiments.py::test_benchmark_export_supplements_missing_metric_without_overriding_result_json`。

### Step 3：更新 compare/export helper

- 操作：检查 `dashboard/exporter.py`：
  - `CSV_COLUMNS` 新增 `seed`、`device`、`train_timesteps`、`checkpoint_dir`、`result_path`。
  - `normalize_result_row()` 输出新增字段。
  - Markdown 表格保留核心列，但可增加 `Device`、`Timesteps`。
- 验证：新增 `tests/test_exporter.py::test_export_includes_new_result_fields`。

### 验收标准

- [ ] 旧 benchmark 与新 benchmark 均可被加载。
- [ ] `result.json` 指标优先级高于 benchmark export。
- [ ] compare/export 不因未知指标缺失而失败。

---

## 模块 8：测试 fixtures 与回归测试补齐

### 概述

- 职责：为新 paper2 实验目录契约构造最小可验证 fixtures，覆盖关键 UI/后端边界情况。
- 前置依赖：模块 1-7
- 预计步骤数：5

### Step 1：创建 Full 17 running fixture

- 操作：创建目录：
  - `tests/fixtures/experiments/paper2_full_17_vscode/`
  - `tests/fixtures/results/`
- 文件：
  - `run.json`：包含 17 个算法，顺序为固定 Full 17 顺序。
  - `state.json`：`status="running"`，`current_index=0`，GRPO running，其他 pending。
  - `process.json`：包含任意测试 pid。
  - `artifacts/GRPO/stdout.log`：含普通训练输出。
  - `artifacts/GRPO/stderr.log`：含 warning 或 tqdm 内容，不代表失败。
- 验证：运行 `python -m pytest tests/test_experiment_reader.py tests/test_state_aggregator_experiments.py -v`。

### Step 2：创建 Quick failed fixture

- 操作：创建目录：
  - `tests/fixtures/experiments/vscode_quick/`
- 文件：
  - `run.json`：GRPO、PPO、SAC。
  - `state.json`：GRPO failed，PPO/SAC pending。
  - `artifacts/GRPO/stdout.log`
  - `artifacts/GRPO/stderr.log`：含 traceback。
- 验证：新增 `tests/test_state_aggregator_experiments.py::test_quick_failed_points_to_grpo_logs`。

### Step 3：创建 completed result fixture

- 操作：在 Full 17 fixture 中补充一个 completed variant 或单独目录：
  - `artifacts/GRPO/result.json` 包含：
    ```json
    {
      "algorithm": "GRPO",
      "environment": "MEC-v1",
      "seed": 42,
      "device": "cpu",
      "train_timesteps": 100000,
      "checkpoint_dir": "experiments/paper2_full_17_vscode/artifacts/GRPO/checkpoints",
      "final_eval": {
        "eval/reward_mean": 1.23,
        "eval/reward_std": 0.1,
        "eval/latency_mean": 12.5,
        "eval/energy_mean": 3.4,
        "eval/comm_score": 0.9
      },
      "status": "success"
    }
    ```
- 验证：新增 `tests/test_experiment_reader.py::test_read_algorithm_result_maps_final_eval`。

### Step 4：创建 edge case fixtures

- 操作：新增 fixtures：
  - `state_running_with_stale_error.json`：running record 带旧 `error`、`exit_code`、`finished_at`。
  - `benchmark_empty.json`：内容为 `[]`。
  - `state_missing_result.json`：completed record 指向不存在 result 文件。
  - `broken_state.json`：半截 JSON。
- 验证：新增测试覆盖：
  - `test_running_record_ignores_stale_error`
  - `test_empty_benchmark_array_is_valid`
  - `test_missing_completed_result_is_warning_not_failure`
  - `test_invalid_state_json_does_not_crash_scan`

### Step 5：端到端 API 测试

- 操作：新增 `tests/test_api_experiments.py`，使用 FastAPI `TestClient`：
  - 构造临时 `DashboardConfig` 指向 fixture 目录。
  - 调用 `create_app(config)`。
  - 覆盖 `/api/health`、`/api/runs`、`/api/runs/{run_id}`、stdout/stderr log API、benchmark API。
- 验证：运行 `python -m pytest tests/test_api_experiments.py -v`。

### 验收标准

- [ ] 每个新数据契约都有 fixture。
- [ ] 所有关键边界条件都有明确测试。
- [ ] 全量测试 `python -m pytest -v` 通过。

---

## 模块 9：文档、启动脚本与最终验收

### 概述

- 职责：同步 README、Windows 启动脚本、迁移说明和验收用例，确保用户可以按新 paper2 输出直接启动 dashboard。
- 前置依赖：模块 1-8
- 预计步骤数：3

### Step 1：更新 README

- 操作：修改 `README.md`：
  - 数据源优先级改为：
    1. `experiments/<run_id>/run.json` + `state.json`
    2. `experiments/<run_id>/artifacts/<ALGORITHM>/result.json`
    3. `results/benchmark_<run_id>.json`
    4. legacy `runs/`、`logs/`、`results/benchmark.json`
  - 启动命令改为：
    ```bash
    python serve_dashboard.py \
      --experiments-dir C:\Users\22003\paper2\paper2\experiments \
      --results-dir C:\Users\22003\paper2\paper2\results \
      --logs-dir C:\Users\22003\paper2\paper2\logs \
      --host 127.0.0.1 --port 8088
    ```
  - 明确 Full 17 与 Quick run id。
  - 明确 dashboard 只读，不启动/停止训练。
- 验证：人工检查 README 不再把 `runs/<run_id>/run_meta.json` 作为推荐主路径。

### Step 2：更新 Windows 启动脚本

- 操作：修改：
  - `start_dashboard.bat`
  - `start_dashboard.vbs` 如存在只负责调用 bat，无需大改。
- `start_dashboard.bat` 需传入：
  - `--experiments-dir C:\Users\22003\paper2\paper2\experiments`
  - `--results-dir C:\Users\22003\paper2\paper2\results`
  - `--logs-dir C:\Users\22003\paper2\paper2\logs`
  - `--benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json` 仅作为 legacy fallback。
- 验证：运行 `start_dashboard.bat` 后访问 `http://127.0.0.1:8088/api/health`，返回 `version=0.3.0`。

### Step 3：新增迁移说明文档

- 操作：新增 `docs/paper2-experiment-architecture-sync.md`，内容包括：
  - 新旧数据源对照表。
  - `state.json` 是唯一实时状态源。
  - artifact 日志路径规则。
  - benchmark export 只用于图表。
  - 四个验收用例：Full 17 running、Quick failed、empty benchmark、running stale error。
- 验证：人工检查文档包含上述四个验收用例。

### 验收标准

- [ ] README 与启动脚本默认指向 `experiments/`。
- [ ] 文档明确不读取 `.index.sqlite3`。
- [ ] 文档明确不通过前端直接 kill 训练进程或删除目录。

---

## 全局验证命令

Codex 完成所有模块后必须按顺序执行：

```bash
python -m pytest -v
python -c "from dashboard.config import create_default_config; from dashboard.api import create_app; app=create_app(create_default_config()); print(app.title)"
python serve_dashboard.py --help
```

如果本地具备 paper2 输出目录，还要执行：

```bash
python serve_dashboard.py \
  --experiments-dir C:\Users\22003\paper2\paper2\experiments \
  --results-dir C:\Users\22003\paper2\paper2\results \
  --logs-dir C:\Users\22003\paper2\paper2\logs \
  --host 127.0.0.1 --port 8088
```

然后手动访问：

```text
http://127.0.0.1:8088/api/health
http://127.0.0.1:8088/api/runs
http://127.0.0.1:8088/api/runs/paper2_full_17_vscode
http://127.0.0.1:8088/api/runs/vscode_quick
http://127.0.0.1:8088
```

## 最终验收用例

### 用例 1：Full 17 初始/运行中

输入：

```text
experiments/paper2_full_17_vscode/run.json
experiments/paper2_full_17_vscode/state.json
```

期望：

- 页面显示 17 个算法。
- 算法顺序为固定 Full 17 顺序。
- 当前算法高亮为 `records[current_index]`。
- 进度按 `completed_algorithms.length / records.length` 计算。
- 当前算法可打开 stdout/stderr。

### 用例 2：Quick 失败

输入：

```text
experiments/vscode_quick/state.json
experiments/vscode_quick/artifacts/GRPO/stdout.log
experiments/vscode_quick/artifacts/GRPO/stderr.log
```

期望：

- 页面显示 Quick 共有 3 个算法。
- GRPO 失败时显示错误摘要。
- 错误详情提供 stdout/stderr 链接。
- PPO/SAC 保持 pending。

### 用例 3：导出结果为空

输入：

```json
[]
```

期望：

- 图表页显示“暂无已完成算法结果”。
- 不把空数组视为加载失败。

### 用例 4：运行中 record 带旧 error

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

- UI 显示 GRPO 运行中。
- 不把旧 `error` 当作当前失败。
- 可以在“历史尝试/调试信息”区域弱提示 `attempts > 1`。

## Codex 执行注意事项

1. 严格按模块顺序执行，不要先改前端再改后端模型。
2. 保留 legacy fallback，不要删除 `log_parser.py`、旧 structured reader、旧 API 路径。
3. 不引入 React/Vue/Vite 等构建工具；继续维护单文件前端。
4. 不实现训练 start/stop/reset/export 后端代理；本轮只读展示。导出按钮可显示 VSCode/CLI 提示。
5. 不读取、不依赖 `experiments/.index.sqlite3`。
6. 所有路径均支持 Windows 与 POSIX；内部使用 `pathlib.Path`。
7. 每个模块完成后运行该模块对应测试；全模块完成后运行全量 pytest。

## 计划质量自检

- 具体性：每一步都指定了文件、函数/类、字段和验证命令。
- 无决策：Codex 不需要判断是否采用新架构；新 `experiments/` 协议优先，legacy fallback 保留。
- 可验证：每一步均有 pytest 或命令行验证方式。
- 连续性：配置 → 模型 → reader → discovery/aggregator → API → 前端 → tests → docs，依赖关系明确。
