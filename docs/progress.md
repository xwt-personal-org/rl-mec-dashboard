# 开发进度

## 当前状态

- 当前阶段：模块 13-14 Mainline-A 适配完成，等待 review
- 最后更新：2026-05-06
- 状态：NEEDS_REVIEW
- plan.md 版本：v3.3
- 整体进度：77 / 77 步骤完成

## 模块进度

### 模块 1-12

- [x] 模块 1-9：paper2 实验状态机适配、API、前端、导出、文档和既有回归
- [x] 模块 10：Patch 10 backup/archive 只读展示与 active run 排除
- [x] 模块 11：备份可见性修复与诊断增强
- [x] 模块 12：本地源文件删除功能

### 模块 13：Mainline-A 新环境与 Full17 Benchmark 数据源适配

- [x] Step 1：新增 paper2 root 与 Mainline-A runtime 配置 `[auto]`
- [x] Step 2：新增 benchmark-only export discovery `[review]`
- [x] Step 3：新增 Mainline-A benchmark schema adapter `[review]`
- [x] Step 4：让 benchmark-only export 可构建完整 RunState `[review]`
- [x] Step 5：新增 Mainline-A diagnostics API `[auto]`
- [x] Step 6：更新 Windows 启动入口与 README `[auto]`
- [x] Step 7：补齐 Mainline-A fixtures `[review]`
- [x] Step 8：模块 13 回归与报告更新 `[review]`

### 模块 14：Mainline-A evidence boundary 与前端展示适配

- [x] Step 1：扩展 API DTO 的 evidence boundary 字段 `[auto]`
- [x] Step 2：前端新增 evidence badge 与 boundary warning `[review]`
- [x] Step 3：compare/chart 避免跨 evidence level 误导 `[review]`
- [x] Step 4：更新结果表格与算法详情字段 `[auto]`
- [x] Step 5：让删除目标覆盖新 benchmark-only exports `[review]`
- [x] Step 6：文档更新：Mainline-A dashboard 使用边界 `[auto]`
- [x] Step 7：全量回归与 v3.3 状态收口 `[review]`

## 已知问题

- 无阻塞问题。
- FastAPI `on_event` 在测试中输出 deprecated warning，属于既有实现警告，本轮未改生命周期结构。
