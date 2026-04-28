# 开发计划

## 元信息

- 项目：`rl-mec-dashboard`
- 目标仓库：`w2030298-art/rl-mec-dashboard`
- 当前分支：`master`
- 生成日期：2026-04-28
- 技术栈：Python 3 + FastAPI + Uvicorn + Server-Sent Events + 原生 HTML/CSS/JavaScript + Chart.js + pytest
- 开发路线：复杂路线，基于 `research-report.md` 与 `architecture.md`
- 核心目标：保持本机、轻量、只读、无前端构建工具的前提下，提升实时监控清晰度、多实验对比、日志排错和页面交互体验。
- 总模块数：11
- 预计步骤总数：52
- 建议开发顺序：模块 0 → 模块 1 → 模块 2 → 模块 3 → 模块 4 → 模块 5 → 模块 6 → 模块 7 → 模块 8 → 模块 9 → 模块 10

## 全局硬约束

1. 保持只读看板：不得增加训练启动、停止、重启、队列、调度等训练控制能力。
2. `POST /api/shutdown` 只关闭 dashboard server，不得控制 paper2 训练进程。
3. 保持原启动命令兼容：
   ```bash
   python serve_dashboard.py --logs-dir logs --benchmark-json results/benchmark.json --host 127.0.0.1 --port 8088
   ```
4. 第一轮不引入数据库，不新增 SQLite/PostgreSQL/Redis。
5. 第一轮不迁移 React/Vite，继续使用 `monitor_dashboard.html` 单页前端。
6. 数据读取优先级：structured run files → `results/benchmark.json` → legacy logs。
7. 所有路径使用 `pathlib.Path`，日志读取使用 `encoding="utf-8", errors="replace"`。
8. 不允许 Codex 自行做技术选型；所有文件名、类名、函数名、API 路径按本文实现。

---

# 模块 0：基线检查与项目骨架准备

## 概述

- 职责：改动前确认现有代码可编译、现有 parser 测试可运行，并创建后续模块化目录。
- 前置依赖：无
- 预计步骤数：4

## Step 1：执行当前基线验证

- 操作：在项目根目录运行：
  ```bash
  python -m py_compile serve_dashboard.py
  python -m pytest test_parsers.py -v
  ```
- 失败处理：如果当前基线失败，先将完整错误写入 `docs/issues.md`，然后做最小修复；不得删除现有测试。
- 验证：两个命令均返回 0。

## Step 2：创建模块化目录结构

- 操作：创建以下结构：
  ```text
  dashboard/
  ├── __init__.py
  ├── api.py
  ├── config.py
  ├── exporter.py
  ├── log_parser.py
  ├── models.py
  ├── protocol_reader.py
  ├── run_discovery.py
  ├── sse.py
  ├── state_aggregator.py
  └── state_store.py

  tests/
  ├── __init__.py
  ├── fixtures/
  │   ├── legacy/
  │   └── structured/
  ├── test_api.py
  ├── test_exporter.py
  ├── test_log_parser.py
  ├── test_models_config.py
  ├── test_protocol_reader.py
  ├── test_run_discovery.py
  └── test_state_aggregator.py
  ```
- 文件内容：
  - `dashboard/__init__.py` 写入：`"""RL-MEC dashboard backend package."""`
  - `tests/__init__.py` 为空。
  - 其他新 Python 文件先写模块 docstring。
- 验证：
  ```bash
  python -c "import dashboard; import dashboard.models; import dashboard.config"
  ```

## Step 3：创建测试夹具说明

- 操作：创建 `tests/fixtures/README.md`，内容：
  ```markdown
  # Test fixtures

  - `legacy/`: legacy `logs/*.log` and `logs/*.err.log` samples.
  - `structured/`: structured `runs/<run_id>/` protocol samples.
  ```
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  assert Path('tests/fixtures/README.md').exists()
  assert Path('tests/fixtures/legacy').exists()
  assert Path('tests/fixtures/structured').exists()
  PY
  ```

## Step 4：添加入口兼容注释

- 操作：在 `serve_dashboard.py` 顶部 docstring 下增加：
  ```python
  # Compatibility note:
  # This file remains the CLI entrypoint. Core implementation is gradually
  # moved into the dashboard package while preserving existing commands.
  ```
- 验证：
  ```bash
  python -m py_compile serve_dashboard.py
  python -m pytest test_parsers.py -v
  ```

## 验收标准

- [ ] 当前基线验证已执行。
- [ ] `dashboard/` package 可导入。
- [ ] `tests/fixtures/` 目录存在。
- [ ] 尚未破坏原 `serve_dashboard.py` 行为。

---

# 模块 1：领域模型与配置解析

## 概述

- 职责：固化 dashboard 的数据模型、API DTO 和 CLI 配置。
- 前置依赖：模块 0
- 预计步骤数：5

## Step 1：实现 `dashboard/models.py` 类型别名与 dataclass

- 操作：在 `dashboard/models.py` 中实现：
  ```python
  from __future__ import annotations

  from dataclasses import asdict, dataclass, field, is_dataclass
  from pathlib import Path
  from typing import Any, Literal

  RunStatus = Literal['idle', 'running', 'finished', 'stalled', 'degraded', 'failed']
  ResultSource = Literal['structured', 'log', 'benchmark_json', 'historical']
  ResultStatus = Literal['pending', 'running', 'finished', 'failed', 'historical']
  LogLevel = Literal['debug', 'info', 'warn', 'error']
  SourceType = Literal['structured', 'legacy_log', 'mixed']
  ```
- 实现 `AlgorithmResult`，字段：
  - `algorithm: str`
  - `reward: float | None = None`
  - `reward_std: float | None = None`
  - `train_time: float | None = None`
  - `latency: float | None = None`
  - `energy: float | None = None`
  - `deadline_miss_rate: float | None = None`
  - `throughput: float | None = None`
  - `comm_score: float | None = None`
  - `update_count: int | None = None`
  - `environment: str = ''`
  - `source: ResultSource = 'log'`
  - `status: ResultStatus = 'finished'`
- 实现 `RecentLogEntry`，字段：`time: str`、`level: LogLevel`、`text: str`、`source_file: str = ''`。
- 实现 `RunMeta`，字段：`run_id`、`created_at`、`started_at`、`finished_at`、`status`、`environment`、`algorithms`、`seeds`、`config_hash`、`config_summary`、`paper2_git_commit`。
- 实现 `RunDescriptor`，字段：`run_id`、`source_type`、`mtime`、`display_name`、`run_dir`、`stdout_file`、`stderr_file`、`summary_file`、`meta_file`。
- 实现 `RunSummary`，字段：`run_id`、`display_name`、`status`、`current_algorithm`、`progress_pct`、`overall_progress`、`total_algorithms`、`updated_at`、`source_type`、`has_error`、`last_error`。
- 实现 `RunState`，字段必须覆盖当前前端所需字段：`run_id`、`status`、`current_algorithm`、`current_step`、`total_step`、`progress_pct`、`it_per_sec`、`eta_seconds`、`elapsed_seconds`、`update_count`、`completed_algorithms`、`results`、`last_error`、`updated_at`、`process_alive`、`recent_logs`、`overall_progress`、`degraded`、`total_algorithms`、`stderr_file`、`stdout_file`、`has_structured_protocol`、`source_type`、`log_offsets`、`event_offsets`、`last_log_time`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.models import RunState, AlgorithmResult
  assert RunState(run_id='r1').run_id == 'r1'
  assert AlgorithmResult(algorithm='GRPO').algorithm == 'GRPO'
  PY
  ```

## Step 2：实现模型转 dict 函数

- 操作：在 `dashboard/models.py` 中实现：
  ```python
  def dataclass_to_dict(obj: Any) -> Any: ...
  def algorithm_result_to_dict(result: AlgorithmResult) -> dict[str, Any]: ...
  def run_summary_to_dict(summary: RunSummary) -> dict[str, Any]: ...
  def run_state_to_dict(state: RunState) -> dict[str, Any]: ...
  ```
- 要求：
  - dataclass 递归转 dict。
  - `Path` 转字符串。
  - list/dict 递归处理。
  - `run_state_to_dict()` 输出字段必须兼容当前前端旧字段，并新增 `has_structured_protocol` 与 `source_type`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.models import RunState, run_state_to_dict
  d = run_state_to_dict(RunState(run_id='x'))
  assert d['run_id'] == 'x'
  assert 'results' in d
  assert 'recent_logs' in d
  assert 'has_structured_protocol' in d
  PY
  ```

## Step 3：实现 `dashboard/config.py`

- 操作：在 `dashboard/config.py` 中实现：
  ```python
  from __future__ import annotations
  import argparse
  from dataclasses import dataclass
  from pathlib import Path

  @dataclass
  class DashboardConfig:
      logs_dir: Path
      benchmark_json: Path
      runs_dir: Path | None
      host: str
      port: int
      scan_interval_sec: float
      stall_threshold_sec: int
      recent_log_limit: int
      sse_interval_sec: float
  ```
- 实现：
  ```python
  def create_default_config() -> DashboardConfig: ...
  def parse_cli_args(argv: list[str] | None = None) -> DashboardConfig: ...
  ```
- CLI 参数：
  - `--logs-dir`, default `logs`
  - `--benchmark-json`, default `results/benchmark.json`
  - `--runs-dir`, default `None`
  - `--host`, default `127.0.0.1`
  - `--port`, default `8088`
  - `--scan-interval`, default `1.0`
  - `--stall-threshold`, default `120`
  - `--recent-log-limit`, default `100`
  - `--sse-interval`, default `1.0`
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.config import parse_cli_args
  cfg = parse_cli_args(['--logs-dir', 'logs', '--runs-dir', 'runs', '--port', '8090'])
  assert str(cfg.logs_dir) == 'logs'
  assert str(cfg.runs_dir) == 'runs'
  assert cfg.port == 8090
  PY
  ```

## Step 4：新增 `tests/test_models_config.py`

- 操作：创建测试：
  - `test_run_state_defaults`
  - `test_algorithm_result_defaults`
  - `test_run_state_to_dict_contains_frontend_fields`
  - `test_parse_cli_args_runs_dir`
  - `test_create_default_config_port`
- 验证：
  ```bash
  python -m pytest tests/test_models_config.py -v
  ```

## Step 5：回归旧 parser 测试

- 操作：本模块不修改 API 行为，不删除 `serve_dashboard.py` 中旧 `RunState`。
- 验证：
  ```bash
  python -m py_compile serve_dashboard.py
  python -m pytest test_parsers.py tests/test_models_config.py -v
  ```

## 验收标准

- [ ] `dashboard/models.py` 包含统一领域模型。
- [ ] `dashboard/config.py` 支持 `--runs-dir`。
- [ ] 新模型测试通过。
- [ ] 原 parser 测试仍通过。

---

# 模块 2：Legacy 日志解析器迁移

## 概述

- 职责：将 `serve_dashboard.py` 中的日志解析函数迁移到 `dashboard/log_parser.py`，并建立新测试。
- 前置依赖：模块 1
- 预计步骤数：5

## Step 1：迁移基础 parser 函数

- 操作：从 `serve_dashboard.py` 复制并整理以下函数到 `dashboard/log_parser.py`：
  - `strip_log_prefix(line: str) -> str`
  - `parse_step_from_tqdm(line: str) -> tuple[int, int, float] | None`
  - `parse_elapsed_from_tqdm(line: str) -> float`
  - `parse_eta_from_tqdm(line: str) -> int`
  - `parse_algo_switch(line: str) -> str | None`
  - `parse_update_count(line: str) -> int | None`
  - `parse_env_from_algo_header(line: str) -> str | None`
  - `parse_benchmark_summary(line: str) -> bool`
  - `parse_algorithm_count_from_summary(line: str) -> int | None`
  - `classify_log_line(line: str) -> str | None`
- 要求：正则行为保持与当前版本一致，尤其不能恢复 `algorithmically`、`warninglight` 这类误判。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.log_parser import parse_algo_switch, parse_update_count
  assert parse_algo_switch('Algorithm: GRPO') == 'GRPO'
  assert parse_update_count('update_count=481436.000') == 481436
  PY
  ```

## Step 2：实现 `parse_result` 返回 `AlgorithmResult`

- 操作：在 `dashboard/log_parser.py` 中实现：
  ```python
  from dashboard.models import AlgorithmResult
  def parse_result(line: str) -> AlgorithmResult | None: ...
  ```
- 支持格式：
  - `[GRPO] reward=11.8355+/-1.0085  time=325.8s`
  - `[GRPO] some text reward=11.0 time=325s`
- 返回字段：`algorithm`、`reward`、`reward_std`、`train_time`、`source='log'`、`status='finished'`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.log_parser import parse_result
  r = parse_result('[GRPO] reward=11.8355+/-1.0085  time=325.8s')
  assert r is not None
  assert r.algorithm == 'GRPO'
  assert r.reward == 11.8355
  PY
  ```

## Step 3：实现统一行解析函数

- 操作：在 `dashboard/log_parser.py` 中新增：
  ```python
  def parse_log_line(line: str, source_file: str = '') -> list[dict]: ...
  ```
- 返回事件类型：
  - `progress`
  - `elapsed`
  - `eta`
  - `update_count`
  - `algorithm_started`
  - `algorithm_finished`
  - `benchmark_finished`
  - `algorithm_count`
  - `log`
- 要求：单行可返回多个事件；解析失败返回空 list，不抛异常。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.log_parser import parse_log_line
  events = parse_log_line('Algorithm: GRPO')
  assert any(e['type'] == 'algorithm_started' for e in events)
  PY
  ```

## Step 4：创建新 parser 测试

- 操作：创建 `tests/test_log_parser.py`，迁移并更新 `test_parsers.py` 中的测试。
- 必测项：
  - 日志前缀清理。
  - tqdm 标准进度。
  - tqdm elapsed-only 格式。
  - result 标准格式。
  - result fallback 格式。
  - algo switch。
  - update_count。
  - env header。
  - benchmark finished。
  - false positive：`saveraerror`、`warninglight`、`algorithmically`、`completely`。
  - true positive：error、warning、Algorithm。
- 验证：
  ```bash
  python -m pytest tests/test_log_parser.py -v
  ```

## Step 5：保留旧测试兼容

- 操作：修改 `test_parsers.py` 为兼容入口测试：
  ```python
  from dashboard.log_parser import parse_algo_switch, parse_result

  def test_legacy_parser_imports_work():
      assert parse_algo_switch('Algorithm: GRPO') == 'GRPO'
      assert parse_result('[GRPO] reward=1.0+/-0.1  time=2.0s') is not None
  ```
- 可选：在 `serve_dashboard.py` re-export parser 函数，保证旧导入方式不坏。
- 验证：
  ```bash
  python -m pytest test_parsers.py tests/test_log_parser.py -v
  ```

## 验收标准

- [ ] `dashboard/log_parser.py` 包含所有 legacy parser。
- [ ] `parse_result()` 返回 `AlgorithmResult`。
- [ ] `parse_log_line()` 返回统一事件。
- [ ] 新旧 parser 测试均通过。

---

# 模块 3：结构化实验协议读取器

## 概述

- 职责：支持读取 `paper2` 新输出协议：`run_meta.json`、`events.jsonl`、`metrics.jsonl`、`summary.json`。
- 前置依赖：模块 1、模块 2
- 预计步骤数：6

## Step 1：创建 structured 测试夹具

- 操作：创建：
  ```text
  tests/fixtures/structured/run_001/
  ├── run_meta.json
  ├── events.jsonl
  ├── metrics.jsonl
  └── summary.json
  ```
- `run_meta.json` 必须包含：`schema_version`、`run_id='run_001'`、`created_at`、`started_at`、`status='running'`、`environment='MEC-v1'`、`algorithms=['GRPO','PPO']`、`seeds=[0,1]`、`config_summary.total_steps=500000`。
- `events.jsonl` 至少包含：
  - `algorithm_started` for GRPO
  - `progress` with `current_step=12000`, `total_step=500000`, `it_per_sec=1020.5`
  - `algorithm_finished` for GRPO with reward/time
  - `log` with `level='warn'`
- `metrics.jsonl` 至少包含 2 行 GRPO metric。
- `summary.json` 至少包含 GRPO final result。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  root = Path('tests/fixtures/structured/run_001')
  for name in ['run_meta.json', 'events.jsonl', 'metrics.jsonl', 'summary.json']:
      assert (root / name).exists()
  PY
  ```

## Step 2：实现 JSON/JSONL 读取工具

- 操作：在 `dashboard/protocol_reader.py` 中实现：
  ```python
  def read_json_file(path: Path) -> dict | list | None: ...
  def read_jsonl_since(path: Path, offset: int = 0) -> tuple[list[dict], int]: ...
  def read_jsonl_tail(path: Path, limit: int = 1000) -> list[dict]: ...
  ```
- 要求：
  - 文件不存在返回 `None` 或空列表。
  - 空行跳过。
  - 非 dict JSONL 行跳过。
  - `read_jsonl_since()` 返回新事件和新的 byte offset。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.protocol_reader import read_json_file, read_jsonl_since
  root = Path('tests/fixtures/structured/run_001')
  assert read_json_file(root / 'run_meta.json')['run_id'] == 'run_001'
  events, offset = read_jsonl_since(root / 'events.jsonl', 0)
  assert len(events) >= 3
  assert offset > 0
  PY
  ```

## Step 3：实现 `StructuredRunReader`

- 操作：在 `dashboard/protocol_reader.py` 中实现：
  ```python
  class StructuredRunReader:
      def __init__(self, run_dir: Path): ...
      def exists(self) -> bool: ...
      def read_meta(self) -> RunMeta | None: ...
      def read_events_since(self, offset: int) -> tuple[list[dict], int]: ...
      def read_metrics_tail(self, limit: int = 1000) -> list[dict]: ...
      def read_summary(self) -> list[AlgorithmResult]: ...
  ```
- 路径：
  - `run_meta.json`
  - `events.jsonl`
  - `metrics.jsonl`
  - `summary.json`
- `read_summary()` 中每个 result：`source='structured'`、`status='finished'`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.protocol_reader import StructuredRunReader
  reader = StructuredRunReader(Path('tests/fixtures/structured/run_001'))
  assert reader.exists()
  assert reader.read_meta().run_id == 'run_001'
  assert reader.read_summary()[0].algorithm == 'GRPO'
  PY
  ```

## Step 4：实现结构化事件标准化

- 操作：实现：
  ```python
  def normalize_structured_event(raw: dict) -> dict | None: ...
  ```
- 支持类型：`algorithm_started`、`progress`、`algorithm_finished`、`log`、`error`、`benchmark_finished`、`run_finished`、`run_failed`。
- `algorithm_finished` 必须把 result 转成 `AlgorithmResult`。
- `log`/`error` 必须包含 `level`、`text`、`source_file='events.jsonl'`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.protocol_reader import normalize_structured_event
  e = normalize_structured_event({'type': 'algorithm_started', 'algorithm': 'GRPO'})
  assert e['type'] == 'algorithm_started'
  r = normalize_structured_event({'type': 'algorithm_finished', 'algorithm': 'GRPO', 'reward': 1.0})
  assert r['result'].algorithm == 'GRPO'
  PY
  ```

## Step 5：新增协议读取测试

- 操作：创建 `tests/test_protocol_reader.py`，覆盖：
  - `read_json_file()`
  - `read_jsonl_since()`
  - `read_jsonl_tail()`
  - `StructuredRunReader.exists()`
  - `StructuredRunReader.read_meta()`
  - `StructuredRunReader.read_summary()`
  - `normalize_structured_event()`
- 验证：
  ```bash
  python -m pytest tests/test_protocol_reader.py -v
  ```

## Step 6：增加损坏 JSON 的降级测试

- 操作：在 `tests/test_protocol_reader.py` 使用 `tmp_path` 创建非法 JSON 文件，断言读取函数抛出 `ValueError` 或返回可控错误，不允许产生未捕获的随机异常类型。
- 验证：
  ```bash
  python -m pytest tests/test_protocol_reader.py -v
  ```

## 验收标准

- [ ] structured fixture 完整。
- [ ] `StructuredRunReader` 可读取 meta、events、metrics、summary。
- [ ] structured result 统一为 `AlgorithmResult`。
- [ ] 协议读取测试通过。

---

# 模块 4：Run 发现与 benchmark JSON 补全

## 概述

- 职责：统一发现 structured runs、legacy runs、mixed runs，并读取 `benchmark.json` 补全结果。
- 前置依赖：模块 1、模块 3
- 预计步骤数：5

## Step 1：创建 legacy 测试夹具

- 操作：创建：
  ```text
  tests/fixtures/legacy/benchmark_full_test.log
  tests/fixtures/legacy/benchmark_full_test.err.log
  tests/fixtures/legacy/benchmark.json
  ```
- `benchmark_full_test.log` 包含：`Algorithm: GRPO`、`[GRPO] reward=11.8355+/-1.0085  time=325.8s`、`Benchmark finished`。
- `benchmark_full_test.err.log` 包含一行 tqdm：`12000/500000`、`1020.50it/s`、`update_count=11000.000`。
- `benchmark.json` 包含 GRPO 的 reward、latency、energy、deadline_miss_rate、throughput、comm_score、total_updates。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  for p in ['benchmark_full_test.log', 'benchmark_full_test.err.log', 'benchmark.json']:
      assert (Path('tests/fixtures/legacy') / p).exists()
  PY
  ```

## Step 2：实现 structured run 发现

- 操作：在 `dashboard/run_discovery.py` 中实现：
  ```python
  def discover_structured_runs(runs_dir: Path | None) -> list[RunDescriptor]: ...
  ```
- 规则：
  - `runs_dir is None` 或不存在，返回空 list。
  - 遍历子目录。
  - 存在 `run_meta.json`、`events.jsonl`、`summary.json` 任一文件即为 structured run。
  - `run_id` 默认目录名；如果 `run_meta.json` 存在且含 `run_id`，优先使用文件值。
  - `mtime` 取结构化文件最大 mtime。
  - `source_type='structured'`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.run_discovery import discover_structured_runs
  runs = discover_structured_runs(Path('tests/fixtures/structured'))
  assert any(r.run_id == 'run_001' for r in runs)
  PY
  ```

## Step 3：实现 legacy run 发现

- 操作：实现：
  ```python
  def discover_legacy_runs(logs_dir: Path) -> list[RunDescriptor]: ...
  ```
- 规则：
  - 扫描 `benchmark*.log`。
  - 跳过 `*.err.log` 作为主文件。
  - stderr 对应文件：`base + '.err.log'`。
  - `run_id` 规则沿用旧代码：去掉 `benchmark_`、`full_`。
  - `source_type='legacy_log'`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.run_discovery import discover_legacy_runs
  runs = discover_legacy_runs(Path('tests/fixtures/legacy'))
  assert runs
  assert runs[0].stdout_file is not None
  PY
  ```

## Step 4：实现统一发现与 mixed 合并

- 操作：实现：
  ```python
  def discover_runs(config: DashboardConfig) -> list[RunDescriptor]: ...
  def select_latest_run(runs: list[RunDescriptor]) -> RunDescriptor | None: ...
  ```
- 合并规则：
  - 同一 `run_id` 同时出现在 structured 和 legacy，合并为 `source_type='mixed'`。
  - mixed run 保留 `run_dir`、`meta_file`、`summary_file`、`stdout_file`、`stderr_file`。
  - 返回按 `mtime desc` 排序。
- 验证：
  ```bash
  python -m pytest tests/test_run_discovery.py -v
  ```

## Step 5：实现 benchmark JSON 读取

- 操作：在 `dashboard/run_discovery.py` 中实现：
  ```python
  def load_benchmark_results(json_path: Path) -> list[AlgorithmResult]: ...
  ```
- 字段映射：
  - `final_reward_mean_mean` → `reward`
  - `final_reward_mean_std` → `reward_std`
  - `train_time_seconds_mean` → `train_time`
  - `final_latency_mean_mean` → `latency`
  - `final_energy_mean_mean` → `energy`
  - `final_deadline_miss_rate_mean` → `deadline_miss_rate`
  - `final_throughput_tasks_per_step_mean` → `throughput`
  - `final_comm_score_mean` → `comm_score`
  - `total_updates_mean` → `update_count`
  - `source='benchmark_json'`
  - `status='historical'`
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.run_discovery import load_benchmark_results
  results = load_benchmark_results(Path('tests/fixtures/legacy/benchmark.json'))
  assert results[0].algorithm == 'GRPO'
  assert results[0].source == 'benchmark_json'
  PY
  ```

## 验收标准

- [ ] structured run 可发现。
- [ ] legacy run 可发现。
- [ ] mixed run 可合并。
- [ ] `benchmark.json` 可补全为 `AlgorithmResult`。
- [ ] run discovery 测试通过。

---

# 模块 5：状态聚合器

## 概述

- 职责：将 structured events、legacy log events、benchmark JSON 合并为统一 `RunState`。
- 前置依赖：模块 1、2、3、4
- 预计步骤数：6

## Step 1：实现 `RunStateAggregator` 初始化与 state 初始化

- 操作：在 `dashboard/state_aggregator.py` 中实现：
  ```python
  class RunStateAggregator:
      def __init__(self, config: DashboardConfig): ...
      def initialize_state(self, descriptor: RunDescriptor) -> RunState: ...
  ```
- 初始化规则：
  - `run_id=descriptor.run_id`
  - `source_type=descriptor.source_type`
  - `stdout_file=str(descriptor.stdout_file or '')`
  - `stderr_file=str(descriptor.stderr_file or '')`
  - `has_structured_protocol=descriptor.source_type in ('structured', 'mixed')`
  - `last_log_time=descriptor.mtime`
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.config import create_default_config
  from dashboard.models import RunDescriptor
  from dashboard.state_aggregator import RunStateAggregator
  desc = RunDescriptor(run_id='x', source_type='structured', mtime=1.0, display_name='x', run_dir=Path('.'))
  state = RunStateAggregator(create_default_config()).initialize_state(desc)
  assert state.has_structured_protocol is True
  PY
  ```

## Step 2：实现 structured events 应用

- 操作：实现：
  ```python
  def apply_structured_events(self, state: RunState, events: list[dict]) -> RunState: ...
  ```
- 规则：
  - `algorithm_started`：设置 `current_algorithm`。
  - `progress`：更新 `current_algorithm`、`current_step`、`total_step`、`it_per_sec`、`eta_seconds`、`progress_pct`、`updated_at`。
  - `algorithm_finished`：加入 `results`，算法加入 `completed_algorithms`。
  - `log`：加入 `recent_logs`。
  - `error`：加入 error log，设置 `last_error` 与 `degraded=True`。
  - `benchmark_finished`/`run_finished`：设置 `status='finished'`。
  - `run_failed`：设置 `status='failed'`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.config import create_default_config
  from dashboard.models import RunState
  from dashboard.state_aggregator import RunStateAggregator
  agg = RunStateAggregator(create_default_config())
  s = agg.apply_structured_events(RunState(run_id='x'), [{'type':'progress','algorithm':'GRPO','current_step':10,'total_step':100,'it_per_sec':2.0}])
  assert s.current_algorithm == 'GRPO'
  assert s.progress_pct == 10.0
  PY
  ```

## Step 3：实现 legacy 文件增量读取

- 操作：实现：
  ```python
  def read_legacy_events_since(self, path: Path, state: RunState) -> list[dict]: ...
  ```
- 规则：
  - 使用 `state.log_offsets[str(path)]` 保存 offset。
  - 文件不存在返回空 list。
  - 文件截断时 offset 重置为 0。
  - 每行调用 `parse_log_line(line, source_file=str(path))`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.config import create_default_config
  from dashboard.models import RunState
  from dashboard.state_aggregator import RunStateAggregator
  agg = RunStateAggregator(create_default_config())
  events = agg.read_legacy_events_since(Path('tests/fixtures/legacy/benchmark_full_test.log'), RunState(run_id='x'))
  assert any(e['type'] == 'algorithm_started' for e in events)
  PY
  ```

## Step 4：实现 legacy events 应用

- 操作：实现：
  ```python
  def apply_legacy_log_events(self, state: RunState, events: list[dict]) -> RunState: ...
  ```
- 规则：与 structured event 使用相同字段；`algorithm_finished` 的 result 保持 `source='log'`；`algorithm_count` 更新 `total_algorithms`；`benchmark_finished` 设置 `finished`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.config import create_default_config
  from dashboard.models import RunState
  from dashboard.state_aggregator import RunStateAggregator
  s = RunStateAggregator(create_default_config()).apply_legacy_log_events(RunState(run_id='x'), [{'type':'algorithm_started','algorithm':'GRPO'}])
  assert s.current_algorithm == 'GRPO'
  PY
  ```

## Step 5：实现结果合并与状态计算

- 操作：实现：
  ```python
  def merge_results(self, state: RunState, fallback_results: list[AlgorithmResult]) -> RunState: ...
  def compute_overall_progress(self, state: RunState) -> RunState: ...
  def compute_status(self, state: RunState) -> RunState: ...
  ```
- 结果优先级：`structured` > `log` > `benchmark_json` > `historical`。
- 字段补全：主结果缺少 `latency`、`energy`、`deadline_miss_rate`、`throughput`、`comm_score`、`update_count` 时，用 fallback 补。
- 状态规则：`finished`/`failed` 保留；超时无更新为 `stalled`；有进度为 `running`；有 degraded 且无更明确状态为 `degraded`；否则 `idle`。
- 验证：
  ```bash
  python -m pytest tests/test_state_aggregator.py -v
  ```

## Step 6：实现 `scan_once`

- 操作：实现：
  ```python
  def scan_once(self, descriptor: RunDescriptor, state: RunState) -> RunState: ...
  ```
- 执行顺序：
  1. 读取 structured meta/events/summary。
  2. 读取 legacy stdout/stderr events。
  3. 读取 benchmark fallback。
  4. 应用事件。
  5. 合并结果。
  6. 计算 overall progress。
  7. 计算 status。
- 异常处理：任何 reader/parser 异常均转换为 `state.degraded=True` 和 `state.last_error`，不向 API 层抛出。
- 验证：
  ```bash
  python -m pytest tests/test_state_aggregator.py -v
  ```

## 验收标准

- [ ] structured events 可更新 `RunState`。
- [ ] legacy logs 可增量更新 `RunState`。
- [ ] benchmark JSON 可补字段。
- [ ] 状态判定集中在 `compute_status()`。
- [ ] 异常 degraded，不导致 API 崩溃。

---

# 模块 6：状态存储、FastAPI 与 SSE 重构

## 概述

- 职责：将全局状态、后台扫描、API 路由和 SSE 迁移到模块化结构，`serve_dashboard.py` 成为薄入口。
- 前置依赖：模块 5
- 预计步骤数：7

## Step 1：实现 `DashboardStateStore`

- 操作：在 `dashboard/state_store.py` 中实现：
  ```python
  class DashboardStateStore:
      def __init__(self, config: DashboardConfig, aggregator: RunStateAggregator): ...
  ```
- 字段：`config`、`aggregator`、`threading.RLock()`、`_run_descriptors`、`_run_states`、`_scanner_thread`、`_stop_event`。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.config import create_default_config
  from dashboard.state_aggregator import RunStateAggregator
  from dashboard.state_store import DashboardStateStore
  cfg = create_default_config()
  assert DashboardStateStore(cfg, RunStateAggregator(cfg)) is not None
  PY
  ```

## Step 2：实现 run index 与状态读取

- 操作：实现：
  ```python
  def refresh_run_index(self) -> list[RunDescriptor]: ...
  def ensure_run_state(self, run_id: str) -> RunState: ...
  def get_runs(self) -> list[RunSummary]: ...
  def get_run_state(self, run_id: str) -> RunState | None: ...
  ```
- 规则：`get_runs()` 返回按更新时间倒序的 summary；API 读取时返回快照，不直接暴露可变对象。
- 验证：
  ```bash
  python -m py_compile dashboard/state_store.py
  ```

## Step 3：实现后台扫描

- 操作：实现：
  ```python
  def scan_all_once(self) -> None: ...
  def start_background_scan(self) -> None: ...
  def shutdown(self) -> None: ...
  ```
- 规则：
  - `scan_all_once()` refresh run index 并扫描每个 run。
  - `start_background_scan()` 不重复启动已有线程。
  - 线程为 daemon。
  - 间隔使用 `config.scan_interval_sec`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  from dashboard.config import DashboardConfig
  from dashboard.state_aggregator import RunStateAggregator
  from dashboard.state_store import DashboardStateStore
  cfg = DashboardConfig(Path('tests/fixtures/legacy'), Path('tests/fixtures/legacy/benchmark.json'), Path('tests/fixtures/structured'), '127.0.0.1', 8088, 1.0, 120, 100, 1.0)
  store = DashboardStateStore(cfg, RunStateAggregator(cfg))
  store.scan_all_once()
  assert store.get_runs()
  PY
  ```

## Step 4：实现 SSE 模块

- 操作：在 `dashboard/sse.py` 中实现：
  ```python
  async def run_snapshot_event_generator(run_id: str, request, store: DashboardStateStore, interval_sec: float): ...
  def create_sse_response(generator): ...
  ```
- 输出格式：
  ```text
  event: snapshot
  data: <json>

  ```
- 验证：
  ```bash
  python -m py_compile dashboard/sse.py
  ```

## Step 5：实现 FastAPI app 与路由

- 操作：在 `dashboard/api.py` 中实现：
  ```python
  def create_app(config: DashboardConfig) -> FastAPI: ...
  def register_routes(app: FastAPI, store: DashboardStateStore) -> None: ...
  ```
- 路由：
  - `GET /`
  - `GET /api/health`
  - `GET /api/runs`
  - `GET /api/runs/{run_id}`
  - `GET /api/runs/{run_id}/events`
  - `POST /api/shutdown`
- `/api/health` 返回：`status`、`version='0.2.0'`、`has_structured_protocol`、`run_count`。
- 验证：
  ```bash
  python -m py_compile dashboard/api.py
  ```

## Step 6：改造 `serve_dashboard.py` 为薄入口

- 操作：将入口改为：
  ```python
  from dashboard.api import create_app
  from dashboard.config import parse_cli_args

  config = parse_cli_args()
  app = create_app(config)

  if __name__ == '__main__':
      import uvicorn
      uvicorn.run(app, host=config.host, port=config.port)
  ```
- 为兼容旧导入，re-export parser 函数：`strip_log_prefix`、`parse_step_from_tqdm`、`parse_result`、`parse_algo_switch`、`parse_update_count`、`parse_env_from_algo_header`、`parse_benchmark_summary`、`classify_log_line`。
- 验证：
  ```bash
  python -m py_compile serve_dashboard.py
  python -c "from serve_dashboard import app; assert app is not None"
  python -m pytest test_parsers.py -v
  ```

## Step 7：新增 API 测试

- 操作：在 `tests/test_api.py` 中使用 `fastapi.testclient.TestClient` 编写：
  - `test_health_endpoint`
  - `test_runs_endpoint`
  - `test_get_run_endpoint`
  - `test_missing_run_returns_404`
- 若 FastAPI 不可用，使用 `pytest.importorskip('fastapi')`。
- 验证：
  ```bash
  python -m pytest tests/test_api.py -v
  ```

## 验收标准

- [ ] `serve_dashboard.py` 成为薄入口。
- [ ] `/api/health`、`/api/runs`、`/api/runs/{run_id}` 可用。
- [ ] SSE 逻辑位于 `dashboard/sse.py`。
- [ ] API 测试通过或在缺少 FastAPI 时合理 skip。

---

# 模块 7：多实验对比与结果导出

## 概述

- 职责：增加 `/api/compare`、CSV 导出、Markdown 导出。
- 前置依赖：模块 6
- 预计步骤数：5

## Step 1：实现 `dashboard/exporter.py`

- 操作：实现：
  ```python
  CSV_COLUMNS = ['run_id','algorithm','reward','reward_std','latency','energy','deadline_miss_rate','throughput','comm_score','train_time','update_count','status','source']
  def normalize_result_row(run_id: str, result: AlgorithmResult) -> dict[str, str]: ...
  def results_to_csv(states: list[RunState]) -> str: ...
  def results_to_markdown(states: list[RunState]) -> str: ...
  ```
- 要求：None 输出为空字符串；CSV 用 `csv.DictWriter`；Markdown 输出标准表格。
- 验证：
  ```bash
  python - <<'PY'
  from dashboard.exporter import results_to_markdown
  from dashboard.models import RunState, AlgorithmResult
  s = RunState(run_id='r1', results=[AlgorithmResult(algorithm='GRPO', reward=1.2)])
  assert 'GRPO' in results_to_markdown([s])
  PY
  ```

## Step 2：实现 compare payload

- 操作：在 `DashboardStateStore` 中实现：
  ```python
  def get_compare_payload(self, run_ids: list[str], metric: str) -> dict: ...
  ```
- 支持 metric：`reward`、`latency`、`energy`、`deadline_miss_rate`、`throughput`、`comm_score`、`train_time`、`update_count`。
- 响应结构：`metric`、`run_ids`、`algorithms`、`series`。
- 无效 metric 抛 `ValueError`。
- 验证：
  ```bash
  python -m py_compile dashboard/state_store.py
  ```

## Step 3：新增 API 路由

- 操作：在 `dashboard/api.py` 中增加：
  - `GET /api/compare?run_ids=a,b,c&metric=reward`
  - `GET /api/export/results.csv?run_ids=a,b,c`
  - `GET /api/export/results.md?run_ids=a,b,c`
- 规则：
  - `run_ids` 为空时默认所有当前 runs。
  - 无效 metric 返回 400。
  - CSV media type：`text/csv`。
  - Markdown media type：`text/markdown`。
- 验证：
  ```bash
  python -m py_compile dashboard/api.py
  ```

## Step 4：新增 exporter 测试

- 操作：创建 `tests/test_exporter.py`，测试：
  - CSV header。
  - CSV 包含 algorithm。
  - Markdown 包含表头与 algorithm。
  - None 值导出为空字符串。
- 验证：
  ```bash
  python -m pytest tests/test_exporter.py -v
  ```

## Step 5：新增 compare/export API 测试

- 操作：在 `tests/test_api.py` 增加：
  - `test_compare_endpoint_reward`
  - `test_compare_endpoint_invalid_metric`
  - `test_export_csv_endpoint`
  - `test_export_markdown_endpoint`
- 验证：
  ```bash
  python -m pytest tests/test_api.py tests/test_exporter.py -v
  ```

## 验收标准

- [ ] `/api/compare` 返回多 run 对比 payload。
- [ ] `/api/export/results.csv` 返回 CSV。
- [ ] `/api/export/results.md` 返回 Markdown。
- [ ] 导出和 API 测试通过。

---

# 模块 8：前端可用性增强

## 概述

- 职责：保持 `monitor_dashboard.html` 单文件，增强 run 总览、筛选、对比、日志排错和导出。
- 前置依赖：模块 6、模块 7
- 预计步骤数：8

## Step 1：重组前端状态对象

- 操作：在 `<script>` 顶部创建：
  ```javascript
  const dashboardState = {
    runs: [],
    currentRunId: null,
    currentRunState: null,
    selectedRunIds: [],
    selectedMetric: 'reward',
    filters: { status: 'all', keyword: '', logLevel: 'all', logKeyword: '', autoScroll: true },
    charts: { rewardChart: null, timeChart: null, compareChart: null },
    sse: { eventSource: null, reconnectTimer: null, connected: false }
  };
  ```
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  assert 'const dashboardState' in html
  assert 'selectedMetric' in html
  PY
  ```

## Step 2：增加页面控件区域

- 操作：新增/调整元素：
  - `id='run-overview'`
  - `id='status-filter'`
  - `id='run-keyword-filter'`
  - `id='compare-panel'`
  - `id='compare-metric'`
  - `id='compareChart'`
  - `id='log-level-filter'`
  - `id='log-keyword-filter'`
  - `id='log-autoscroll-toggle'`
  - `id='export-csv-btn'`
  - `id='export-md-btn'`
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for token in ['run-overview', 'compare-panel', 'log-level-filter', 'export-csv-btn']:
      assert token in html
  PY
  ```

## Step 3：实现 API client 函数

- 操作：在 JS 中增加：
  - `apiGetJson(url)`
  - `loadRuns()`
  - `fetchInitialRunState(runId)`
  - `loadCompareData()`
  - `exportResults(format)`
- 规则：
  - `loadRuns()` 调 `/api/runs`。
  - `fetchInitialRunState()` 调 `/api/runs/${runId}`。
  - `loadCompareData()` 调 `/api/compare?run_ids=${ids}&metric=${metric}`。
  - `exportResults('csv')` 打开 `/api/export/results.csv?run_ids=...`。
  - `exportResults('md')` 打开 `/api/export/results.md?run_ids=...`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for fn in ['apiGetJson', 'loadCompareData', 'exportResults']:
      assert fn in html
  PY
  ```

## Step 4：实现 run overview 渲染与筛选

- 操作：实现：
  - `applyRunFilters(runs)`
  - `renderRunOverview(runs)`
  - `selectRun(runId)`
- 展示字段：status、run_id、current_algorithm、progress_pct、overall_progress、total_algorithms、updated_at、source_type、last_error。
- 每个 run 增加 checkbox，用于 compare selected runs。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for fn in ['applyRunFilters', 'renderRunOverview', 'selectRun']:
      assert fn in html
  PY
  ```

## Step 5：增强详情、结果表和图表

- 操作：实现/改造：
  - `renderRunDetail(state)`
  - `renderMetricCards(state)`
  - `renderResultsTable(results)`
  - `updateCharts(state)`
- 结果表字段：algorithm、environment、reward、latency、energy、deadline_miss_rate、throughput、comm_score、train_time、status、source。
- 空数据时显示 placeholder，不允许 Chart.js update 抛错。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for token in ['deadline_miss_rate', 'throughput', 'comm_score']:
      assert token in html
  PY
  ```

## Step 6：增强日志排错面板

- 操作：实现：
  - `applyLogFilters(logs)`
  - `renderLogs(logs)`
  - `copyLogLine(text)`
  - `renderErrorSummary(logs)`
- 规则：
  - level filter：all/error/warn/info。
  - keyword filter：对 log text 做 lowercase includes。
  - auto-scroll 仅当 `dashboardState.filters.autoScroll === true`。
  - error summary 显示最近 error；无 error 显示 `No recent errors`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for fn in ['applyLogFilters', 'copyLogLine', 'renderErrorSummary']:
      assert fn in html
  PY
  ```

## Step 7：实现 compare panel

- 操作：实现：
  - 初始化 `compareChart`。
  - `renderCompareChart(payload)`。
  - `renderCompareTable(payload)`。
- 规则：
  - 默认 metric 为 `reward`。
  - 至少两个 selected run 时请求 compare API。
  - 少于两个 run 时显示 `Select at least two runs to compare.`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  for token in ['compareChart', 'renderCompareChart', 'Select at least two runs']:
      assert token in html
  PY
  ```

## Step 8：修正 Stop Dashboard 文案

- 操作：
  - 按钮文案改为 `Stop Dashboard Server`。
  - JS 函数改名为 `stopDashboardServer()`。
  - confirm 文案必须包含：`This only stops the dashboard server. It does not stop paper2 training jobs.`
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  html = Path('monitor_dashboard.html').read_text(encoding='utf-8')
  assert 'Stop Dashboard Server' in html
  assert 'does not stop paper2 training jobs' in html
  assert 'stopDashboardServer' in html
  PY
  ```

## 验收标准

- [ ] 页面有 run overview。
- [ ] 支持状态和关键词筛选。
- [ ] 支持多 run 选择与 metric 对比。
- [ ] 支持 CSV/Markdown 导出按钮。
- [ ] 日志支持 level、keyword、auto-scroll。
- [ ] Stop Dashboard 文案不误导。
- [ ] 未引入前端构建工具。

---

# 模块 9：端到端测试与回归验证

## 概述

- 职责：执行全部自动化测试与 legacy/structured smoke test。
- 前置依赖：模块 8
- 预计步骤数：4

## Step 1：运行全部测试

- 操作：
  ```bash
  python -m pytest -v
  ```
- 验证：所有测试通过；若 FastAPI 缺失导致 API 测试被 `pytest.importorskip` skip，记录到 `docs/issues.md`。

## Step 2：执行 legacy-only smoke test

- 操作：
  ```bash
  python serve_dashboard.py --logs-dir tests/fixtures/legacy --benchmark-json tests/fixtures/legacy/benchmark.json --host 127.0.0.1 --port 8088
  ```
- 验证：
  - `GET /api/health` 返回 `status=ok`。
  - `GET /api/runs` 返回非空 runs。
  - `GET /api/runs/{run_id}` 返回 `results`、`recent_logs`、`status`。

## Step 3：执行 structured smoke test

- 操作：
  ```bash
  python serve_dashboard.py --logs-dir tests/fixtures/legacy --benchmark-json tests/fixtures/legacy/benchmark.json --runs-dir tests/fixtures/structured --host 127.0.0.1 --port 8088
  ```
- 验证：
  - `/api/runs` 中至少一个 run 的 `source_type` 为 `structured` 或 `mixed`。
  - `/api/runs/{run_id}` 中 `has_structured_protocol=true`。
  - `/api/compare?run_ids=run_001&metric=reward` 返回 JSON。
  - `/api/export/results.csv?run_ids=run_001` 返回 CSV。
  - `/api/export/results.md?run_ids=run_001` 返回 Markdown。

## Step 4：前端手工验收

- 操作：浏览器打开 `http://127.0.0.1:8088`。
- 检查：
  - [ ] 页面无白屏。
  - [ ] Run Overview 显示 run 列表。
  - [ ] 点击 run 后详情更新。
  - [ ] SSE 状态正常。
  - [ ] Reward/Training Time 图表不报错。
  - [ ] 日志 level 和 keyword filter 可用。
  - [ ] compare panel 在至少两个 run 时可用，一个 run 时显示 placeholder。
  - [ ] CSV/Markdown 导出可用。
  - [ ] Stop Dashboard Server 文案明确不停止训练任务。

## 验收标准

- [ ] 自动化测试通过。
- [ ] legacy-only 模式可运行。
- [ ] structured 模式可运行。
- [ ] 前端 smoke test 通过。

---

# 模块 10：文档与迁移说明

## 概述

- 职责：更新 README 和本地协议说明，便于后续维护及 paper2 输出端适配。
- 前置依赖：模块 9
- 预计步骤数：3

## Step 1：更新 `README.md`

- 操作：补充：
  - 新启动参数 `--runs-dir`。
  - structured protocol 说明。
  - legacy fallback 说明。
  - `Stop Dashboard Server` 只关闭 dashboard，不停止训练任务。
  - 测试命令：`python -m pytest -v`。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  text = Path('README.md').read_text(encoding='utf-8')
  assert '--runs-dir' in text
  assert 'structured' in text.lower() or '结构化' in text
  assert '不停止训练' in text or 'does not stop' in text.lower()
  PY
  ```

## Step 2：新增 `docs/structured-protocol.md`

- 操作：创建文档，必须包含：
  - `runs/<run_id>/` 目录结构。
  - `run_meta.json` schema。
  - `events.jsonl` event types。
  - `metrics.jsonl` sample。
  - `summary.json` sample。
  - dashboard 数据源优先级。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  p = Path('docs/structured-protocol.md')
  assert p.exists()
  text = p.read_text(encoding='utf-8')
  for token in ['run_meta.json', 'events.jsonl', 'metrics.jsonl', 'summary.json']:
      assert token in text
  PY
  ```

## Step 3：新增 `docs/paper2-dashboard-writer-reference.md`

- 操作：创建 paper2 输出端参考文档，包含伪代码：
  ```python
  class DashboardRunWriter:
      def __init__(self, run_dir: Path, run_id: str, config_summary: dict): ...
      def write_meta(self, meta: dict) -> None: ...
      def append_event(self, event: dict) -> None: ...
      def append_metric(self, metric: dict) -> None: ...
      def write_summary(self, summary: dict) -> None: ...
      def mark_finished(self) -> None: ...
      def mark_failed(self, error: str) -> None: ...
  ```
- 文档必须声明：该 writer 属于 paper2 集成参考，dashboard 仓库不直接控制训练。
- 验证：
  ```bash
  python - <<'PY'
  from pathlib import Path
  p = Path('docs/paper2-dashboard-writer-reference.md')
  assert p.exists()
  text = p.read_text(encoding='utf-8')
  assert 'DashboardRunWriter' in text
  assert 'legacy' in text.lower()
  PY
  ```

## 验收标准

- [ ] README 已更新。
- [ ] `docs/structured-protocol.md` 已创建。
- [ ] `docs/paper2-dashboard-writer-reference.md` 已创建。
- [ ] 最终测试命令通过。

---

# 总体验收标准

- [ ] 原启动命令继续可用。
- [ ] 新参数 `--runs-dir` 可用。
- [ ] 没有 structured runs 时，legacy logs 仍能展示。
- [ ] 有 structured runs 时，dashboard 优先读取 JSON/JSONL。
- [ ] `GET /api/health` 返回服务状态。
- [ ] `GET /api/runs` 返回实验总览。
- [ ] `GET /api/runs/{run_id}` 返回完整状态快照。
- [ ] `GET /api/runs/{run_id}/events` 返回 SSE snapshot。
- [ ] `GET /api/compare` 支持多实验指标对比。
- [ ] `GET /api/export/results.csv` 支持 CSV 导出。
- [ ] `GET /api/export/results.md` 支持 Markdown 导出。
- [ ] 前端支持 run overview、状态筛选、关键词筛选、详情展示、日志过滤、多 run 对比、导出。
- [ ] `Stop Dashboard Server` 文案明确不停止 paper2 训练。
- [ ] parser、protocol reader、run discovery、state aggregator、exporter、API 测试通过。
- [ ] 不引入数据库。
- [ ] 不引入前端构建工具。
- [ ] Codex 执行中无需再做技术选型。
