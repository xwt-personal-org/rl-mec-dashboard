# Windows Start Menu Launcher

## 目标

Windows Start Menu Launcher 只简化 dashboard server 的启动入口。它复用现有 `start_dashboard.vbs` 和 `start_dashboard.bat`，不替代 dashboard server 逻辑。

Dashboard 仍只读 paper2 训练输出文件；该入口不启动、不停止、不重启 paper2 训练任务。

## 安装

在项目根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
```

默认安装到当前用户开始菜单：

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk
```

## 启动

从 Windows 开始菜单搜索 `RL-MEC Dashboard`，或按以下路径启动：

```text
Start / 开始菜单 -> RL-MEC Dashboard -> RL-MEC Dashboard
```

启动后脚本会打开：

```text
http://127.0.0.1:8088
```

## 卸载

在项目根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
```

卸载脚本只删除开始菜单中的 `.lnk` 文件和空的 `RL-MEC Dashboard` 菜单目录，不删除项目文件。

## 故障排查

- 找不到快捷方式：重新运行安装命令。
- PowerShell execution policy 阻止：确认命令包含 `-ExecutionPolicy Bypass`。
- 点击后浏览器打不开：手动访问 `http://127.0.0.1:8088`，并用 `start_dashboard.bat` 查看控制台日志。
- Python 路径失效：检查 `start_dashboard.bat` 中 `PYTHON=` 是否仍指向 paper2 虚拟环境。

## 为什么本轮不做浏览器扩展

普通浏览器扩展不能直接启动本地 `.bat` / `.vbs`。

真正的一键启动需要 Native Messaging Host 和系统注册表配置，维护成本更高，也超出本轮只增加启动入口的范围。

Start Menu 快捷方式已经能满足一键启动 dashboard server 的目标，复杂度更低。
