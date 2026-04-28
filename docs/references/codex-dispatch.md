# Codex 任务派发

进入连续执行模式。目标项目为 `rl-mec-dashboard`。从 **模块 0：基线检查与项目骨架准备 Step 1：执行当前基线验证** 开始继续，按 `docs/plan.md` 执行到全部模块完成。

## 启动

1. 读取 `docs/progress.md`，定位当前未完成的第一个步骤。
2. 读取 `docs/plan.md`，加载完整开发计划。
3. 读取 `docs/architecture.md`，确认模块边界、API、目录结构和结构化协议。
4. 读取以下参考文件：
   - `docs/references/ref-structured-experiment-protocol.md`
   - `docs/references/ref-paper2-dashboard-writer.md`
5. 确认当前仓库根目录存在：
   - `serve_dashboard.py`
   - `monitor_dashboard.html`
   - `test_parsers.py`
   - `README.md`
   - `PLAN.md`

## 执行规则

- 从当前进度点开始，按 `docs/plan.md` 的模块顺序和步骤顺序逐步执行。
- 每个步骤完成后立即运行该步骤中列出的验证命令。
- 验证通过后直接进入下一个步骤，不要停下来请求确认。
- 每完成一个完整模块后，批量更新 `docs/progress.md`。
- 所有模块完成后，输出完成报告。
- 保持只读 dashboard，不得增加训练启动、停止、重启、任务队列、任务调度。
- `POST /api/shutdown` 只能关闭 dashboard server，不得控制 paper2 训练进程。
- 保持原启动命令兼容：
  ```bash
  python serve_dashboard.py --logs-dir logs --benchmark-json results/benchmark.json --host 127.0.0.1 --port 8088
  ```
- 新增 `--runs-dir` 参数时必须保持该参数可选，不能破坏不传 `--runs-dir` 的 legacy 模式。
- 第一轮不得引入数据库。
- 第一轮不得迁移 React/Vite 或引入前端构建工具。
- 所有路径使用 `pathlib.Path`。
- 文件读取使用 `encoding="utf-8", errors="replace"`。
- 不得引入 `docs/plan.md` 未指定的三方依赖。

## 仅以下情况停下

- 当前步骤验证失败，且自行诊断修复 2 次后仍失败。
- 遇到 `docs/plan.md` 未覆盖的技术决策。
- 需要用户提供外部资源，例如真实训练日志、API 密钥、未提交文件、设计稿。
- 当前步骤的前置依赖未完成。
- 发现执行计划与仓库实际结构出现不可自动修复的冲突。

停下前必须：

1. 将问题记录到 `docs/issues.md`。
2. 在记录中写明：
   - 所在模块
   - 所在步骤
   - 失败命令
   - 错误输出摘要
   - 已尝试的 2 次修复
   - 需要用户决策的具体问题
3. 输出阻塞报告。

## 进度更新规则

- 以模块为粒度批量更新 `docs/progress.md`。
- 不要每完成一个小步骤就写一次进度文件。
- 完成模块后，将该模块所有完成的 Step checkbox 改为 `[x]`。
- 将“当前阶段”更新为下一个未完成模块的第一个未完成步骤。
- 全部完成后，将“当前阶段”更新为 `全部完成`，状态更新为 `完成`。

## 禁止行为

- 不要每完成一个小步骤就停下来请求确认。
- 不要偏离 `docs/plan.md` 自行添加功能。
- 不要引入 `docs/plan.md` 未指定的依赖。
- 不要为了通过测试删除测试。
- 不要把 dashboard 改成训练控制台。
- 不要把 dashboard 与 paper2 训练函数直接耦合。
- 不要迁移 React/Vite。
- 不要引入 SQLite/PostgreSQL/Redis。
- 不要破坏 legacy 日志模式。
- 不要删除 `monitor_dashboard.html` 单页入口。
- 不要删除 `serve_dashboard.py` CLI 入口。

## 完成后输出

完成后输出以下表格：

| 模块 | 状态 | 主要改动 | 验证命令 | 结果 |
|------|------|----------|----------|------|
| 模块 0 | completed / blocked | ... | ... | ... |
| 模块 1 | completed / blocked | ... | ... | ... |

并输出：

- 遇到的 issues 列表；没有则写“无”。
- 被跳过的测试；没有则写“无”。
- 需要用户后续处理的事项；没有则写“无”。
- 最终启动命令。
- 最终 API smoke test 命令。

现在开始执行。
