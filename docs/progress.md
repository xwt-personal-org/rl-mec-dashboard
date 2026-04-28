# 开发进度

## 当前状态
- 当前阶段：全部完成
- 最后更新：2026-04-28
- 状态：完成

## 模块进度

### 模块 0：基线检查与项目骨架准备
- [x] Step 1: 执行当前基线验证
- [x] Step 2: 创建模块化目录结构
- [x] Step 3: 创建测试夹具说明
- [x] Step 4: 添加入口兼容注释

### 模块 1：领域模型与配置解析
- [x] Step 1: 实现 `dashboard/models.py` 类型别名与 dataclass
- [x] Step 2: 实现模型转 dict 函数
- [x] Step 3: 实现 `dashboard/config.py`
- [x] Step 4: 新增 `tests/test_models_config.py`
- [x] Step 5: 回归旧 parser 测试

### 模块 2：Legacy 日志解析器迁移
- [x] Step 1: 迁移基础 parser 函数
- [x] Step 2: 实现 `parse_result` 返回 `AlgorithmResult`
- [x] Step 3: 实现统一行解析函数
- [x] Step 4: 创建新 parser 测试
- [x] Step 5: 保留旧测试兼容

### 模块 3：结构化实验协议读取器
- [x] Step 1: 创建 structured 测试夹具
- [x] Step 2: 实现 JSON/JSONL 读取工具
- [x] Step 3: 实现 `StructuredRunReader`
- [x] Step 4: 实现结构化事件标准化
- [x] Step 5: 新增协议读取测试
- [x] Step 6: 增加损坏 JSON 的降级测试

### 模块 4：Run 发现与 benchmark JSON 补全
- [x] Step 1: 创建 legacy 测试夹具
- [x] Step 2: 实现 structured run 发现
- [x] Step 3: 实现 legacy run 发现
- [x] Step 4: 实现统一发现与 mixed 合并
- [x] Step 5: 实现 benchmark JSON 读取

### 模块 5：状态聚合器
- [x] Step 1: 实现 `RunStateAggregator` 初始化与 state 初始化
- [x] Step 2: 实现 structured events 应用
- [x] Step 3: 实现 legacy 文件增量读取
- [x] Step 4: 实现 legacy events 应用
- [x] Step 5: 实现结果合并与状态计算
- [x] Step 6: 实现 `scan_once`

### 模块 6：状态存储、FastAPI 与 SSE 重构
- [x] Step 1: 实现 `DashboardStateStore`
- [x] Step 2: 实现 run index 与状态读取
- [x] Step 3: 实现后台扫描
- [x] Step 4: 实现 SSE 模块
- [x] Step 5: 实现 FastAPI app 与路由
- [x] Step 6: 改造 `serve_dashboard.py` 为薄入口
- [x] Step 7: 新增 API 测试

### 模块 7：多实验对比与结果导出
- [x] Step 1: 实现 `dashboard/exporter.py`
- [x] Step 2: 实现 compare payload
- [x] Step 3: 新增 API 路由
- [x] Step 4: 新增 exporter 测试
- [x] Step 5: 新增 compare/export API 测试

### 模块 8：前端可用性增强
- [x] Step 1: 重组前端状态对象
- [x] Step 2: 增加页面控件区域
- [x] Step 3: 实现 API client 函数
- [x] Step 4: 实现 run overview 渲染与筛选
- [x] Step 5: 增强详情、结果表和图表
- [x] Step 6: 增强日志排错面板
- [x] Step 7: 实现 compare panel
- [x] Step 8: 修正 Stop Dashboard 文案

### 模块 9：端到端测试与回归验证
- [x] Step 1: 运行全部测试
- [x] Step 2: 执行 legacy-only smoke test
- [x] Step 3: 执行 structured smoke test
- [x] Step 4: 前端手工验收

### 模块 10：文档与迁移说明
- [x] Step 1: 更新 `README.md`
- [x] Step 2: 新增 `docs/structured-protocol.md`
- [x] Step 3: 新增 `docs/paper2-dashboard-writer-reference.md`

## 已知问题

（暂无）

## 进度维护规则

- Codex 每完成一个完整模块后，批量更新本文件中对应模块的 checkbox。
- 当前阶段应指向下一个未完成步骤。
- 如果验证失败且自行修复 2 次仍失败，将问题写入 `docs/issues.md` 并停止执行。
- 如果遇到 `docs/plan.md` 未覆盖的技术决策，将问题写入 `docs/issues.md` 并停止执行。
