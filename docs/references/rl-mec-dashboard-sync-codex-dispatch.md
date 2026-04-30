# Codex 任务派发：rl-mec-dashboard 对齐 paper2 新实验编排架构

进入连续执行模式。从 **模块 1：配置入口与路径约定迁移 Step 1** 开始执行。

## 启动

1. 读取 `docs/progress.md`，定位当前未完成的第一个步骤。
2. 读取 `docs/plan.md`，加载完整开发计划。
3. 本次为简单路线迁移任务，没有 `docs/references/` 技术调研文件。
4. 当前仓库：`w2030298-art/rl-mec-dashboard`。
5. 当前技术栈：Python 3 + FastAPI + Uvicorn；单文件原生 HTML/CSS/JavaScript + Chart.js；SSE；pytest。

## 计划模块

- 模块 1：配置入口与路径约定迁移（5 steps）
- 模块 2：领域模型对齐 paper2 实验状态机（5 steps）
- 模块 3：新增 paper2 实验文件读取器（7 steps）
- 模块 4：实验发现与状态聚合改造（7 steps）
- 模块 5：API 层适配新实验视图与日志读取（6 steps）
- 模块 6：前端 `monitor_dashboard.html` 迁移（6 steps）
- 模块 7：benchmark 兼容与导出映射（3 steps）
- 模块 8：测试 fixtures 与回归测试补齐（5 steps）
- 模块 9：文档、启动脚本与最终验收（3 steps）

## 执行规则

- 从当前进度点开始，严格按 `docs/plan.md` 的模块顺序和步骤顺序逐步执行。
- 每个步骤完成后，立即运行该步骤列出的验证命令。
- 验证通过后直接进入下一步骤，不要停下来请求确认。
- 每完成一个完整模块后，批量更新 `docs/progress.md` 中该模块所有已完成步骤。
- 每完成一个完整模块后，运行该模块对应测试命令；所有模块完成后运行全局验证命令。
- 保留 legacy fallback：不要删除 `dashboard/log_parser.py`、旧 structured reader、旧 API 路径。
- 新 paper2 `experiments/` 协议优先级最高：实时状态以 `experiments/<run_id>/state.json` 为准。
- 不读取、不依赖 `experiments/.index.sqlite3`。
- 不实现训练 start/stop/reset/export 后端代理；本轮 dashboard 保持只读。
- 不引入 React/Vue/Vite 等构建工具；继续维护单文件前端 `monitor_dashboard.html`。
- 所有路径使用 `pathlib.Path`，必须兼容 Windows 与 POSIX。

## 仅以下情况停下报告

- 当前步骤验证失败，且自行诊断修复 2 次后仍失败。
- 遇到 `docs/plan.md` 未覆盖的技术决策。
- 需要用户提供外部资源、凭证、真实 paper2 输出目录或无法从 fixtures 构造的数据。
- 当前步骤的前置依赖未完成。
- 发现计划要求与仓库实际文件结构存在不可自动调和的冲突。

## 失败处理规则

验证失败时：

1. 阅读失败堆栈、相关源码和测试。
2. 在不偏离 `docs/plan.md` 的前提下修复。
3. 最多重试 2 次。
4. 仍失败则在 `docs/issues.md` 追加记录，格式如下：

```markdown
## [YYYY-MM-DD HH:mm] 模块 X Step Y：<步骤标题>

- 状态：阻塞
- 失败命令：`<command>`
- 错误摘要：<error summary>
- 已尝试修复：
  1. <attempt 1>
  2. <attempt 2>
- 需要用户决策/资源：<具体说明>
```

## 进度更新规则

- 以模块为粒度批量更新 `docs/progress.md`。
- 模块内步骤验证通过后，可在内存中记录完成状态；完成整个模块后统一写入 `docs/progress.md`。
- `docs/progress.md` 的模块名、步骤编号、步骤标题必须与 `docs/plan.md` 保持一致。
- 不要每完成一个小步骤就停下来等待用户确认。

## 全局验证命令

所有模块完成后按顺序运行：

```bash
python -m pytest -v
python -c "from dashboard.config import create_default_config; from dashboard.api import create_app; app=create_app(create_default_config()); print(app.title)"
python serve_dashboard.py --help
```

如果本地具备 paper2 输出目录，再运行：

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

## 禁止行为

- 不要偏离 `docs/plan.md` 自行添加功能。
- 不要引入 `docs/plan.md` 未指定的依赖。
- 不要删除 legacy fallback。
- 不要用 `results/benchmark.json` 判断当前实验状态。
- 不要用 stderr 是否为空判断失败。
- 不要通过前端 kill 训练进程、删除实验目录或修改 paper2 训练输出。
- 不要把 Quick smoke test 作为正式论文结果展示。

## 完成后输出

完成后输出以下报告：

| 模块 | 状态 | 验证命令 | 结果 |
|---|---|---|---|
| 模块 1 | completed/blocked | `<command>` | pass/fail |
| 模块 2 | completed/blocked | `<command>` | pass/fail |
| 模块 3 | completed/blocked | `<command>` | pass/fail |
| 模块 4 | completed/blocked | `<command>` | pass/fail |
| 模块 5 | completed/blocked | `<command>` | pass/fail |
| 模块 6 | completed/blocked | `<command>` | pass/fail |
| 模块 7 | completed/blocked | `<command>` | pass/fail |
| 模块 8 | completed/blocked | `<command>` | pass/fail |
| 模块 9 | completed/blocked | `<command>` | pass/fail |

同时列出：

- 修改的文件清单。
- 新增的测试清单。
- 遇到的 issues 列表；如无则写“无”。
- 需要用户后续手动验证的浏览器页面和真实 paper2 输出目录验证项。

现在开始执行。
