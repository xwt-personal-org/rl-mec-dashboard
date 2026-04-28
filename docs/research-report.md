# 技术调研报告

## 0. 元信息

- 项目名称：`rl-mec-dashboard`
- 目标项目：`w2030298-art/rl-mec-dashboard`
- 当前阶段：阶段 1 — 技术调研
- 生成日期：2026-04-28
- 交付位置建议：`docs/research-report.md`
- 仓库改动：无。本报告只作为本地 `docs/` 文档交付，不修改 GitHub 仓库。
- 调研限制：本报告基于已读取的 GitHub 仓库文件、用户需求和稳定工程实践整理；未执行外部在线资料检索。

---

## 1. 调研范围

### 1.1 已确认需求

用户对下一阶段的目标描述为：当前功能没有完全明确，只希望 dashboard 更好用；允许在必要时修改 `paper2` 输出格式；必要时可以引入数据库；必要时可以改动前端架构；保持只读看板；优先级由规划方评判。

用户明确关注的“更好用”方向：

- A. 实时监控更清楚
- B. 多实验对比更方便
- D. 日志排错更方便
- E. 页面交互和视觉更舒服

不作为本轮优先目标：

- 训练控制、启动/停止训练、任务队列、调度系统
- 多用户权限、登录鉴权
- 云端实验平台化
- 直接引入复杂 MLOps 平台

### 1.2 仓库现状摘要

当前项目是一个轻量只读实验看板：

- 后端：`serve_dashboard.py`
  - FastAPI 应用
  - SSE 实时状态推送
  - 日志扫描与解析
  - `benchmark.json` 历史结果补全
  - 内存态 `RunState`
  - `POST /api/shutdown` 看板服务关闭接口

- 前端：`monitor_dashboard.html`
  - 原生 HTML/CSS/JavaScript
  - Chart.js 柱状图
  - SSE 订阅
  - run selector
  - 状态卡、进度条、结果表、日志窗口

- 测试：`test_parsers.py`
  - 主要覆盖日志解析函数
  - 暂未系统覆盖 API、SSE、状态聚合、前端交互

- 原始计划：`PLAN.md`
  - 目标是本机单用户、只读、日志解析型轻看板
  - 优先解析 `logs/*.err.log` 和 `logs/*.log`
  - 输出 RunState 快照
  - 前端通过 SSE 每秒刷新

### 1.3 调研关键词

本轮调研围绕以下工程问题展开：

- 轻量实验看板架构
- RL/ML 实验实时监控
- 结构化实验输出协议
- 日志解析 fallback
- Server-Sent Events 实时推送
- JSONL event stream
- 多实验对比
- 本地只读 dashboard
- Chart.js 单页看板
- FastAPI 模块化
- SQLite 是否必要
- 前端是否需要 React/Vite 重构

### 1.4 覆盖时间范围

- 工程实践覆盖：2020—2026 常见本地实验监控与轻量 dashboard 方案
- 外部资料检索：未执行
- 论文检索：不需要。该需求不涉及新的 RL 算法、模型训练理论或学术方法实现，属于实验工程与可视化系统设计。

---

## 2. 技术方案对比

| 方案 | 来源 | 核心原理 | 优势 | 劣势 | 适用场景 | 可行性评分 |
|---|---|---|---|---|---|---|
| 方案 A：保留 FastAPI + SSE + 单页 HTML，增加结构化输出协议与后端模块化 | 当前项目演进 | `paper2` 输出 `run_meta.json`、`metrics.jsonl`、`events.jsonl`、`summary.json`；dashboard 优先读结构化文件，日志正则解析作为 fallback | 改动可控；保留现有使用方式；最适合本机只读场景；显著提升实时性、稳定性、可测试性；不引入重前端栈 | 前端复杂度继续增长时，单文件 HTML 会逐渐难维护 | 当前最合适：希望更好用，但不需要平台化 | 5/5 |
| 方案 B：引入 SQLite 作为本地实验索引与缓存层 | 本地实验管理常见实践 | 后端扫描日志和结构化文件后写入 SQLite；前端查询统一 API | 历史 run 多时查询快；支持复杂筛选、排序、对比；便于生成报告 | 增加 schema migration、缓存一致性、导入逻辑；当前仓库规模可能过度设计 | run 数量较多、历史实验需要长期查询时 | 3.5/5 |
| 方案 C：前端迁移到 Vite + React + ECharts/Recharts | Web 前端工程化常见方案 | 将页面拆成组件、状态管理、图表组件、路由页面 | 可维护性强；适合多页面、多组件交互；视觉与交互升级空间大 | 初期重构成本高；需要构建链；对本地轻看板可能偏重 | 前端功能继续扩大到多页工作台时 | 3/5 |
| 方案 D：直接接入 TensorBoard / MLflow UI / W&B 风格工具 | 现成 MLOps/实验追踪工具 | 训练过程输出指标到成熟实验平台，由平台负责图表、对比、实验记录 | 功能成熟；多实验对比强；有既有生态 | RL-MEC 自定义字段、日志、算法进度、ETA、deadline/energy 等指标需要适配；本地简洁体验下降；可能超出只读轻看板目标 | 需要标准化实验管理平台，而不是定制轻看板时 | 2.5/5 |
| 方案 E：继续只增强现有正则日志解析，不设计结构化协议 | 当前最小改动路径 | 保持 `logs/*.log` / `*.err.log` 正则解析，补充更多 pattern | 改动最小；短期能快速补若干字段 | 易脆弱；训练输出格式稍变就失效；多实验对比和错误定位受限；长期维护成本高 | 临时补丁，不适合本轮“更好用”目标 | 2/5 |

---

## 3. 推荐方案

### 3.1 首选方案：方案 A

推荐采用：

> **FastAPI + SSE + 结构化实验输出协议 + 后端模块化 + 单页前端体验增强**

该方案最符合当前约束：

- 保持只读看板，不引入训练控制复杂性
- 不强行引入数据库
- 不强行迁移 React
- 允许修改 `paper2` 输出格式，从根源减少日志解析不稳定性
- 保留现有启动方式和本机单用户体验
- 可为后续 SQLite 或 React 迁移预留边界

### 3.2 备选方案：方案 B

当满足以下任一条件时，再引入 SQLite：

- 历史 run 数量超过 100 个
- 单个 run 指标点超过 10 万级，前端直接加载 JSONL 性能明显下降
- 需要复杂查询：按算法、seed、环境、时间范围、状态、配置摘要组合筛选
- 需要 dashboard 启动后快速展示历史数据，而不是每次扫描文件系统

### 3.3 不推荐本轮直接执行的方案

#### 不建议本轮直接迁移 React

原因：

- 现有前端虽为单文件，但功能还在可控边界内
- 当前更大的问题是数据协议、模块边界、状态聚合和测试，而不是框架
- 若先迁移 React，容易把主要工作量消耗在构建链和 UI 重写上，无法优先改善实验监控质量

#### 不建议本轮直接引入 MLflow / TensorBoard / W&B 替代

原因：

- 当前 dashboard 需要展示 RL-MEC 特定指标与训练进度：
  - 当前算法
  - 当前 step / total step
  - it/s
  - ETA
  - deadline miss rate
  - energy
  - latency
  - throughput
  - comm score
  - recent logs
  - stalled/degraded 状态
- 现有通用平台很难无缝满足“本机轻量、只读、定制字段、打开即用”的目标
- 可在后续将结构化输出协议设计得兼容外部平台导出，而不是立即替换 dashboard

---

## 4. 建议目标架构方向

### 4.1 核心设计原则

1. **结构化数据优先，日志解析兜底**
   - dashboard 不应长期依赖 fragile regex 作为主数据源
   - `paper2` 应输出 dashboard 友好的结构化文件
   - 日志解析只作为老 run 和异常场景 fallback

2. **只读看板保持只读**
   - 不增加训练启动、停止、重启、任务队列
   - `POST /api/shutdown` 仅用于停止 dashboard 服务，不控制训练
   - 与 `paper2` 训练进程保持低耦合

3. **先模块化后重构前端**
   - 后端先拆出 parser、scanner、state、schema、api
   - 前端先在单文件中增加清晰的数据结构和交互能力
   - 后续如果前端复杂度继续上升，再迁移到 Vite + React

4. **状态聚合要可测试**
   - `RunState` 不应只作为临时内存对象散落在 `serve_dashboard.py`
   - 状态更新规则、stalled 判断、finished 判断、degraded 判断都应有单元测试

5. **兼容旧数据**
   - 旧的 `logs/*.log`、`*.err.log`、`results/benchmark.json` 继续可读
   - 新协议优先，旧解析器 fallback
   - 不要求用户立即重跑所有历史实验

---

## 5. 建议结构化实验输出协议

建议在 `paper2` 中为每个 run 输出如下目录：

```text
runs/
└── <run_id>/
    ├── run_meta.json
    ├── metrics.jsonl
    ├── events.jsonl
    ├── summary.json
    ├── stdout.log
    └── stderr.log
```

dashboard 数据源优先级：

1. `runs/<run_id>/run_meta.json`
2. `runs/<run_id>/metrics.jsonl`
3. `runs/<run_id>/events.jsonl`
4. `runs/<run_id>/summary.json`
5. `results/benchmark.json`
6. `logs/benchmark*.log`
7. `logs/benchmark*.err.log`

### 5.1 `run_meta.json`

用途：描述一次实验运行的静态元信息。

建议 schema：

```json
{
  "schema_version": 1,
  "run_id": "20260428_143000",
  "project": "paper2",
  "experiment_name": "rl_mec_benchmark_full",
  "created_at": "2026-04-28T14:30:00+08:00",
  "started_at": "2026-04-28T14:30:02+08:00",
  "finished_at": null,
  "status": "running",
  "environment": "mec_default",
  "algorithms": ["GRPO", "PPO", "SAC"],
  "total_algorithms": 17,
  "total_steps_per_algorithm": 500000,
  "seeds": [42],
  "config": {
    "config_path": "configs/xxx.yaml",
    "device": "cpu",
    "notes": ""
  }
}
```

关键规则：

- `schema_version` 必须存在，用于后续兼容升级
- `run_id` 必须与目录名一致
- `status` 只允许：
  - `created`
  - `running`
  - `finished`
  - `failed`
  - `stalled`
  - `unknown`
- `algorithms` 顺序即 benchmark 执行顺序

### 5.2 `metrics.jsonl`

用途：记录高频训练指标。每一行是一个 JSON 对象。

建议字段：

```json
{
  "time": "2026-04-28T14:31:10+08:00",
  "algorithm": "GRPO",
  "step": 12000,
  "total_step": 500000,
  "it_per_sec": 1732.4,
  "elapsed_seconds": 48,
  "eta_seconds": 282,
  "reward": 10.23,
  "loss": null,
  "latency": 0.012,
  "energy": 0.87,
  "deadline_miss_rate": 0.03,
  "throughput": 41.2,
  "comm_score": 0.92,
  "update_count": 11800
}
```

关键规则：

- 写入模式采用 append-only
- dashboard 只读取新增 offset，避免反复加载整文件
- 高频指标可以降采样输出，例如每 1 秒或每 N step 一条
- 缺失字段写 `null`，不要省略字段，便于前端稳定渲染

### 5.3 `events.jsonl`

用途：记录低频事件、状态切换、错误、警告。

建议字段：

```json
{
  "time": "2026-04-28T14:30:02+08:00",
  "level": "info",
  "type": "algorithm_started",
  "algorithm": "GRPO",
  "message": "Algorithm GRPO started",
  "data": {
    "seed": 42
  }
}
```

事件类型建议：

- `run_started`
- `run_finished`
- `run_failed`
- `algorithm_started`
- `algorithm_finished`
- `metric_checkpoint`
- `warning`
- `error`
- `log`
- `summary_written`

关键规则：

- 错误事件必须包含 `message`
- 若有异常堆栈，写入 `data.traceback`
- dashboard 的日志窗口优先展示 `events.jsonl` 中的 warning/error/info，而不是反复正则扫原始日志

### 5.4 `summary.json`

用途：记录 run 最终聚合结果。

建议字段：

```json
{
  "schema_version": 1,
  "run_id": "20260428_143000",
  "status": "finished",
  "started_at": "2026-04-28T14:30:02+08:00",
  "finished_at": "2026-04-28T16:10:12+08:00",
  "duration_seconds": 6010,
  "results": [
    {
      "algorithm": "GRPO",
      "environment": "mec_default",
      "reward": 11.8355,
      "reward_std": 1.0085,
      "latency": 0.012,
      "energy": 0.87,
      "deadline_miss_rate": 0.03,
      "throughput": 41.2,
      "comm_score": 0.92,
      "train_time": 325.8,
      "update_count": 481436
    }
  ]
}
```

关键规则：

- `summary.json` 是 dashboard 完成态结果表的主数据源
- 如果 `summary.json` 存在且 `metrics.jsonl` 缺失，dashboard 仍可展示 finished run
- 如果 run 失败，`status=failed` 且提供 `error_summary`

---

## 6. Dashboard 功能优先级建议

### P0：可用性与可靠性

P0 目标：不改变项目使用心智，显著改善“打开后能不能快速看懂当前实验”。

#### P0-1：后端模块化

将 `serve_dashboard.py` 拆分为：

```text
rl_mec_dashboard/
├── __init__.py
├── app.py
├── config.py
├── models.py
├── run_discovery.py
├── structured_reader.py
├── log_parser.py
├── state_store.py
├── aggregator.py
└── sse.py
```

拆分目标：

- `models.py`：定义 `RunState`、`RunSummary`、`MetricPoint`、`DashboardEvent`
- `run_discovery.py`：发现 run 目录、旧日志文件、benchmark json
- `structured_reader.py`：读取 `run_meta.json`、`metrics.jsonl`、`events.jsonl`、`summary.json`
- `log_parser.py`：保留当前正则解析逻辑
- `aggregator.py`：把结构化数据和日志 fallback 聚合成前端快照
- `state_store.py`：维护内存状态、offset、cache、mtime
- `app.py`：只保留 FastAPI 路由定义

#### P0-2：实验总览增强

新增或增强 `GET /api/runs` 返回字段：

```json
{
  "run_id": "20260428_143000",
  "status": "running",
  "current_algorithm": "GRPO",
  "progress_pct": 42.5,
  "overall_progress": 5.42,
  "total_algorithms": 17,
  "updated_at": 1777357800.0,
  "started_at": "2026-04-28T14:30:02+08:00",
  "finished_at": null,
  "result_count": 5,
  "has_error": false,
  "error_summary": "",
  "source": "structured"
}
```

前端 run selector 升级为 run overview：

- 状态 badge
- 搜索框
- 状态筛选：running / finished / failed / stalled / degraded
- 排序：最近更新 / 开始时间 / 完成进度 / 结果数
- 一键只看活跃 run

#### P0-3：单实验详情增强

当前页面应强化：

- 状态卡：增加 `source=structured/log_fallback/mixed`
- 当前算法卡：显示算法序号，例如 `6 / 17`
- 进度条：同时展示当前算法进度和总 benchmark 进度
- 指标表：明确展示 reward、latency、energy、deadline miss、throughput、comm score
- 图表：
  - Reward ranking
  - Latency ranking
  - Energy ranking
  - Deadline miss ranking
- 日志窗口：
  - error / warning / info 筛选
  - 关键词过滤
  - 自动滚动开关
  - 只看当前算法日志
  - 复制错误摘要

#### P0-4：测试补齐

需要新增测试：

```text
tests/
├── test_log_parser.py
├── test_structured_reader.py
├── test_run_discovery.py
├── test_aggregator.py
├── test_api.py
└── fixtures/
    ├── structured_run/
    ├── legacy_log_run/
    └── failed_run/
```

最低验收：

- 旧日志解析测试继续通过
- 结构化 run 能被发现
- `metrics.jsonl` 增量读取 offset 正确
- failed run 能展示 `status=failed`
- API `GET /api/runs`、`GET /api/runs/{run_id}` 返回稳定 schema
- SSE 能至少推送一次合法 snapshot

### P1：多实验对比

P1 目标：服务论文实验分析。

#### P1-1：多 run 对比接口

新增：

```text
GET /api/compare?run_ids=a,b,c&metric=reward
GET /api/algorithms
GET /api/metrics
```

响应建议：

```json
{
  "metric": "reward",
  "runs": ["run_a", "run_b"],
  "algorithms": ["GRPO", "PPO"],
  "table": [
    {
      "algorithm": "GRPO",
      "run_a": 11.2,
      "run_b": 12.1,
      "best": 12.1,
      "best_run": "run_b"
    }
  ]
}
```

#### P1-2：对比视图

前端新增：

- 勾选多个 run
- 选择 metric
- 算法维度对比表
- best value 高亮
- mean/std 展示
- 导出 CSV / Markdown

#### P1-3：导出功能

新增接口：

```text
GET /api/runs/{run_id}/export.csv
GET /api/runs/{run_id}/export.json
POST /api/compare/export.md
```

导出 Markdown 表格用于论文记录和实验日志。

### P2：可选结构升级

#### P2-1：SQLite

仅当 run 数量和查询复杂度上来后引入。

建议表：

```text
runs
metrics
events
results
```

但第一轮不建议实现。

#### P2-2：React/Vite

满足以下条件再迁移：

- 页面超过 3 个主要视图
- 图表交互复杂
- 单文件 HTML 超过 1500 行且修改风险明显升高
- 需要可复用组件和路由

当前建议先保留原生前端。

---

## 7. 关键参考资料

本轮不需要下载论文。建议后续 Codex 只参考以下项目内资料：

| 资料 | 作用 | 使用方式 |
|---|---|---|
| `README.md` | 当前功能、启动方式、技术栈说明 | 保证改造后使用方式不破坏 |
| `PLAN.md` | 原始轻看板需求与接口约定 | 作为 backward compatibility 基线 |
| `serve_dashboard.py` | 当前后端实现 | 拆分模块时逐段迁移 |
| `monitor_dashboard.html` | 当前前端实现 | 保留 UI 能力并逐步增强 |
| `test_parsers.py` | 当前解析器测试 | 迁移后保证测试继续覆盖旧 parser |

外部稳定技术参考方向：

- FastAPI 路由组织与测试
- Server-Sent Events 基本协议
- JSON Lines append-only event stream
- Chart.js 图表配置
- pytest fixture 与临时目录测试
- SQLite 本地缓存设计（仅 P2）

---

## 8. 需要蒸馏给 Codex 的技术要点

### 8.1 总体实现策略

Codex 后续应按如下策略实现：

1. 不直接推翻当前项目。
2. 先将现有 `serve_dashboard.py` 的逻辑拆成模块。
3. 保留现有 API 路径，确保前端不立即失效。
4. 新增结构化 reader，使 dashboard 优先读取 `runs/<run_id>/` 结构化数据。
5. 保留旧日志 parser，作为 legacy fallback。
6. 前端先在 `monitor_dashboard.html` 内增强，不立即引入 React。
7. 所有新增模块必须配套 pytest。
8. 不修改 GitHub 仓库，用户会手动把 docs 放入本地。

### 8.2 数据源优先级

聚合器必须按固定优先级读取：

```text
structured run dir
  → run_meta.json
  → metrics.jsonl
  → events.jsonl
  → summary.json
legacy files
  → results/benchmark.json
  → logs/benchmark*.log
  → logs/benchmark*.err.log
```

如果结构化文件存在但部分缺失：

- `run_meta.json` 缺失：从目录名和日志文件推断 run_id
- `metrics.jsonl` 缺失：当前进度从日志解析 fallback
- `summary.json` 缺失：结果从 `benchmark.json` 或 log result fallback
- `events.jsonl` 缺失：recent logs 从原始日志分类 fallback

### 8.3 Snapshot schema

前端消费的 run snapshot 应稳定为：

```json
{
  "run_id": "string",
  "status": "idle|running|finished|failed|stalled|degraded|unknown",
  "source": "structured|legacy|mixed",
  "current_algorithm": "string",
  "current_algorithm_index": 0,
  "total_algorithms": 17,
  "current_step": 0,
  "total_step": 500000,
  "progress_pct": 0.0,
  "overall_progress": 0.0,
  "it_per_sec": 0.0,
  "eta_seconds": 0,
  "elapsed_seconds": 0,
  "update_count": 0,
  "completed_algorithms": [],
  "results": [],
  "recent_logs": [],
  "last_error": "",
  "error_summary": "",
  "updated_at": 0.0,
  "started_at": null,
  "finished_at": null,
  "degraded": false,
  "stderr_file": "",
  "stdout_file": ""
}
```

字段兼容规则：

- 原有字段不得随意删除。
- 新增字段可以加，但前端必须对缺失字段容错。
- `status` 枚举必须固定，不允许随意拼新值。
- `source` 用于向用户解释当前数据是结构化来源还是日志解析 fallback。

### 8.4 状态判定规则

状态判定必须集中在 `aggregator.py` 或等价模块中，不允许散落在 API 层。

建议规则：

```text
if summary.status == "finished":
    status = "finished"
elif any fatal error event:
    status = "failed"
elif latest metric mtime within active threshold:
    status = "running"
elif current_step > 0 and no update for STALL_THRESHOLD_SEC:
    status = "stalled"
elif parser/reader raised recoverable error:
    status = "degraded"
else:
    status = "idle"
```

注意：

- `degraded` 代表 dashboard 数据读取有问题，不一定代表训练失败。
- `failed` 代表训练 run 自身失败。
- `stalled` 代表训练可能卡住或没有新指标。
- `finished` 优先级高于 stalled。

### 8.5 前端增强规则

保持单文件前端时，Codex 应至少重构 JS 组织：

```javascript
const api = { ... };
const state = { ... };
const charts = { ... };
const render = { ... };
const sse = { ... };
const utils = { ... };
```

不得继续把所有逻辑堆在无结构的全局函数中。

新增交互：

- run 搜索
- 状态筛选
- 指标图表切换
- 日志级别筛选
- 日志关键词过滤
- 自动滚动开关
- 导出按钮

### 8.6 测试策略

每个新增模块必须对应测试文件：

- `test_structured_reader.py`
- `test_run_discovery.py`
- `test_aggregator.py`
- `test_api.py`

测试必须使用 `tmp_path` 构造临时 run 目录，不依赖用户真实路径。

API 测试使用 FastAPI `TestClient`。

最小测试命令：

```bash
python -m pytest -v
```

若项目暂未有依赖文件，后续计划阶段应明确是否新增：

```text
requirements.txt
```

并写入：

```text
fastapi
uvicorn
pytest
httpx
```

### 8.7 风险点

| 风险 | 影响 | 应对 |
|---|---|---|
| `paper2` 输出协议改动影响主训练代码 | 可能破坏算法实验 | 只新增结构化旁路输出，不替换原日志 |
| 前端单文件继续膨胀 | 可维护性下降 | 先组织 JS 命名空间，后续再迁移 React |
| 多数据源合并产生不一致 | 展示错误 | 明确 source 优先级和覆盖规则 |
| 旧日志格式多样 | fallback 解析不稳定 | 保持 parser 测试，解析失败进入 degraded |
| SSE 连接反复重连 | 体验差 | 保留自动重连，并增加连接状态提示 |
| 图表点数过多 | 前端卡顿 | P1 或 P2 时加入采样和 SQLite 缓存 |

---

## 9. 结论

本项目不需要先做算法/论文层面的技术调研。真正的关键是实验工程层面的数据协议、模块化、状态聚合、可测试性和交互设计。

推荐路线：

```text
阶段 2 架构设计：
  设计结构化输出协议 + 后端模块拆分 + 前端增强边界 + API schema

阶段 3 计划制定：
  形成 Codex 可逐步执行的文件级开发计划

阶段 4 交付打包：
  生成 progress.md、issues.md、codex-dispatch.md 等 docs 文件
```

最终建议：

- P0：结构化协议 + 后端模块化 + 总览/详情/日志体验增强 + 测试补齐
- P1：多 run 对比 + Markdown/CSV 导出
- P2：SQLite 和 React/Vite 迁移，暂不进入第一轮
