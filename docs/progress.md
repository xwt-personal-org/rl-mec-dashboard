# 开发进度

## 当前状态

- 当前阶段：模块 11-12、前端视觉整理与本地验证环境整理完成，等待 review
- 最后更新：2026-05-02 03:12
- 状态：NEEDS_REVIEW
- plan.md 版本：v3.2
- 整体进度：62 / 62 步骤完成

## 模块进度

### 模块 1-10

- [x] 模块 1-9：paper2 实验状态机适配、API、前端、导出、文档和既有回归
- [x] 模块 10：Patch 10 backup/archive 只读展示与 active run 排除

### 模块 11：备份可见性修复与诊断增强

- [x] Step 1：新增 `backup_scan_dirs` 配置与 `--backup-scan-dir`
- [x] Step 2：扩展 backup 目录命名兼容 `[REVIEW]`
- [x] Step 3：支持多 backup scan roots `[REVIEW]`
- [x] Step 4：新增 archive-only 发现 `[REVIEW]`
- [x] Step 5：新增 `/api/backups/diagnostics`
- [x] Step 6：前端新增全局 Backups 面板、诊断提示与 backup 可选展示 `[REVIEW]`

### 模块 12：本地源文件删除功能

- [x] Step 1：新增删除领域模型
- [x] Step 2：新增 `dashboard/delete_service.py` 与路径安全策略 `[REVIEW]`
- [x] Step 3：实现删除 target discovery `[REVIEW]`
- [x] Step 4：新增删除 API `[REVIEW]`
- [x] Step 5：前端新增 Danger Zone `[REVIEW]`
- [x] Step 6：删除后状态刷新与用户反馈
- [x] Step 7：文档与启动说明更新
- [x] Step 8：全量回归与报告更新 `[REVIEW]`

### 用户反馈补充

- [x] backup 作为看板选项展示，不只出现在备份列表中 `[REVIEW]`
- [x] 删除 target 覆盖 dashboard 已识别的 active run、backup、archive-only、structured run、legacy log、benchmark export、global benchmark JSON `[REVIEW]`
- [x] 前端视觉与模块组织整理：监控主线前置，Danger Zone 下移，日志合并到底部 `[REVIEW]`
- [x] 本地验证环境整理：关闭 8093 测试端口，启动 8088 正式端口，补齐 Playwright fallback

## 已知问题

- 无阻塞问题。
- FastAPI `on_event` 在测试中输出 deprecated warning，属于既有实现警告，本轮未改生命周期结构。
- 本轮 sandbox 创建的 QA 临时目录出现 ACL 异常，已通过 `.gitignore` 与 `pytest.ini` 避免污染 git 和 pytest 收集。
