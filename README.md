# RL-MEC Training Dashboard

轻量级网页看板，用于实时监控 RL-MEC Benchmark 训练任务状态。

## 功能

- **实时状态监控**：当前算法、训练进度、速度 (it/s)、ETA
- **多运行切换**：支持同时监控多个历史/当前训练运行
- **SSE 实时推送**：前端通过 Server-Sent Events 每秒自动刷新
- **结果可视化**：Reward 对比图、训练时间柱状图（Chart.js）
- **历史数据补全**：自动加载 `benchmark.json` 补充缺失指标
- **一键停止**：页面内"Stop Dashboard"按钮可优雅关闭后端服务

## 启动方式

### 方式一：前台控制台（推荐）

双击 `start_dashboard_visible.bat`
- 弹出控制台窗口，显示服务器日志
- 自动用 Chrome 打开看板（未安装则回退到系统默认浏览器）
- **关闭控制台窗口 = 100% 停止所有后台进程**

### 方式二：静默后台

双击 `start_dashboard.vbs`
- 无窗口，静默启动
- 关闭浏览器后 Python 进程仍在后台运行
- 可通过页面"Stop Dashboard"按钮停止

### 方式三：命令行

```bash
C:\Users\22003\paper2\paper2\.venv\Scripts\python.exe serve_dashboard.py \
    --logs-dir C:\Users\22003\paper2\paper2\logs \
    --benchmark-json C:\Users\22003\paper2\paper2\results\benchmark.json \
    --host 127.0.0.1 --port 8088
```

访问：`http://127.0.0.1:8088`

## 文件说明

| 文件 | 说明 |
|------|------|
| `serve_dashboard.py` | FastAPI 后端，日志解析、SSE 服务 |
| `monitor_dashboard.html` | 单文件前端，Chart.js 图表 |
| `test_parsers.py` | 解析器单元测试（pytest） |
| `start_dashboard.bat` | 被 vbs 调用的底层启动脚本 |
| `start_dashboard.vbs` | 静默启动入口 |
| `start_dashboard_visible.bat` | 前台控制台启动入口 |
| `PLAN.md` | 原始需求规格 |

## 技术栈

- **后端**：Python 3, FastAPI, Uvicorn
- **前端**：原生 HTML + CSS + JavaScript, Chart.js
- **通信**：Server-Sent Events (SSE)
- **测试**：pytest

## 开发

运行测试：
```bash
python -m pytest test_parsers.py -v
```

## License

MIT
