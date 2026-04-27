## 定制轻看板实施方案（本机单用户、只读、日志解析）

### Summary
- 目标：做一个本机可访问的网页轻看板，实时展示训练任务状态、当前算法进度、速度、ETA、已完成算法结果。
- 范围：只读监控，不做启动/停止训练控制。
- 数据源：优先解析 `logs/*.err.log`（tqdm 实时进度）和 `logs/*.log`（算法切换与最终 reward）。
- 交付标准：打开浏览器即可看到实时刷新看板，能准确反映当前 500000 全量任务进度。

### Implementation Changes
- 后端服务（Python，FastAPI + SSE）：
  - 新增一个轻量监控服务入口（建议新增 [serve_dashboard.py](C:\Users\22003\paper2\paper2\scripts\serve_dashboard.py)）。
  - 维护 `RunState` 内存对象，字段固定为：`run_id`、`status`、`current_algorithm`、`current_step`、`total_step`、`progress_pct`、`it_per_sec`、`eta_seconds`、`elapsed_seconds`、`update_count`、`completed_algorithms`、`results[]`、`last_error`、`updated_at`。
  - 增量读取日志：为每个 log 文件维护 `offset`，每秒读新增内容，避免整文件反复解析。
- 解析器规则（确定实现，不留决策）：
  - `stdout(.log)` 解析：
    - `Algorithm: XXX` 识别当前算法切换。
    - `[XXX] reward=... time=...s` 识别算法完成结果并加入 `results[]`。
  - `stderr(.err.log)` 解析：
    - `Training <Algo>Agent: ... a/b ... it/s ...` 解析 `current_step/total_step/it_per_sec`。
    - 包含 `<HH:MM:SS` 的 tqdm ETA 段转为 `eta_seconds`；左侧已耗时转 `elapsed_seconds`。
    - `update_count=...` 若存在则更新 `update_count`。
  - 运行状态判定：
    - `running`：进程存在且日志仍在增长。
    - `finished`：检测到 benchmark 总表输出或进程结束且最后算法有完成记录。
    - `stalled`：进程存在但日志超过阈值（默认 120s）无增长。
- 前端看板（无构建工具，原生 HTML + JS）：
  - 新增静态页面（建议 [monitor_dashboard.html](C:\Users\22003\paper2\paper2\scripts\monitor_dashboard.html)）。
  - 页面布局固定四区：
    - 顶部状态卡：运行状态、当前算法、总进度、ETA。
    - 中部进度卡：当前算法 step 进度条、it/s、update_count。
    - 结果表：已完成算法的 reward/time 列表，按完成顺序展示。
    - 日志窗口：最近 50 行关键日志（错误优先）。
  - 实时更新机制：前端通过 SSE 订阅状态流，断线后 3 秒自动重连。
- 服务编排与使用方式：
  - 命令固定：`python scripts/serve_dashboard.py --logs-dir logs --host 127.0.0.1 --port 8088`
  - 浏览器访问固定：`http://127.0.0.1:8088`

### Public APIs / Interfaces
- `GET /api/runs`
  - 返回可监控 run 列表（按最后更新时间倒序）。
- `GET /api/runs/{run_id}`
  - 返回单 run 当前快照（`RunState` 全字段）。
- `GET /api/runs/{run_id}/events`
  - SSE 流，每秒推送一次快照，事件名 `snapshot`。
- `GET /`
  - 返回轻看板静态页面。
- 错误约定：
  - run 不存在返回 `404`。
  - 解析失败不抛 500，返回 `status=degraded` 并附 `last_error`。

### Test Plan
- 解析器单测：
  - 用真实样例行覆盖 GRPO/PPO/SAC/DDPG 的 tqdm 格式差异。
  - 覆盖有/无 `update_count`、有/无 ETA、中文/ANSI 警告干扰行。
  - 验证算法切换与完成结果提取准确性。
- 服务集成测：
  - 用临时日志文件模拟“追加写入”，验证 `RunState` 随增量正确推进。
  - 验证 SSE 连续推送、断开重连后状态一致。
- 手工验收：
  - 训练进行中打开看板，确认 5 秒内看到正确当前算法和 step 进度。
  - 算法完成后结果表自动新增一行。
  - 训练结束后状态转 `finished` 且最终结果可完整查看。

### Assumptions / Defaults
- 默认仅监控本机 `logs/benchmark_full_*.log|err.log`，单用户访问，不做鉴权。
- 默认只支持“读取状态”，不提供训练进程控制接口。
- 默认优先监控最新活跃 run（可在 `GET /api/runs` 中切换）。
- 默认刷新粒度 1 秒；若 CPU 占用升高，降为 2 秒。
- 预计工作量：1.5~2.5 天（含解析单测与手工验收）。
