# Plan Patch — Windows 菜单栏一键启动入口

## 元信息

- 变更日期：2026-04-30
- 变更类型：新增功能
- 关联原 plan.md 版本：`docs/plan.md` 当前完成版；`docs/progress.md` 显示全部模块已完成，最后更新 2026-04-28
- 目标仓库：`w2030298-art/rl-mec-dashboard`
- 需求摘要：将 dashboard 入口从手动点击 `.vbs` / `.bat` 简化为 Windows Start Menu 一键启动；浏览器扩展方案暂不进入本 patch
- 涉及模块数：1
- 新增步骤数：4
- 修改步骤数：1
- 删除步骤数：0
- 微调研：不需要；本次是 Windows shell 快捷方式集成，不涉及算法、模型、论文或新技术选型

## 操作清单（Codex 必须严格按此处理）

### [MODIFY] 模块 9 — Step 1：更新 README

**原步骤**（参考 `docs/plan.md` 模块 9 Step 1）：

> Step 1：更新 README

**修改后**：

- 操作：修改项目根目录 `README.md` 的 `## 启动方式` 小节。
- 在现有 `### 命令行` 之前新增推荐入口小节：

  ```markdown
  ### Windows 菜单栏一键启动（推荐）

  首次安装快捷方式：

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
  ```

  安装后从 Windows 开始菜单启动：

  ```text
  Start / 开始菜单 → RL-MEC Dashboard → RL-MEC Dashboard
  ```

  该入口会静默调用 `start_dashboard.vbs`，再由 `start_dashboard.bat --hidden` 启动 dashboard server 并打开浏览器。

  卸载开始菜单快捷方式：

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
  ```

  说明：此入口只启动 dashboard server，不启动、不停止、不重启 paper2 训练任务。
  ```

- 保留现有 `### Windows 启动脚本` 小节，并补充一句：
  - `start_dashboard.vbs` / `start_dashboard.bat` 仍作为底层兼容入口保留；普通使用优先从 Windows 开始菜单启动。
- 不修改 `Stop Dashboard Server` 的含义；仍必须明确它只关闭 dashboard server。
- 不引入浏览器扩展相关安装说明，避免让用户误以为普通扩展可以直接启动本地可执行脚本。

**关键代码指引**：

- README 中不要写死除现有项目路径以外的新绝对路径。
- PowerShell 命令必须使用 `-NoProfile -ExecutionPolicy Bypass -File`，降低用户首次运行 `.ps1` 被策略阻止的概率。
- 文案必须明确：Start Menu 入口复用现有 `start_dashboard.vbs`，不替代 server 逻辑。

**验证**：

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text(encoding="utf-8")
assert "Windows 菜单栏一键启动" in text
assert "install_start_menu_shortcut.ps1" in text
assert "uninstall_start_menu_shortcut.ps1" in text
assert "start_dashboard.vbs" in text
assert "不启动、不停止、不重启 paper2 训练任务" in text or "不启动、不停止、不重启" in text
PY
```

---

### [ADD] 模块 9 — Step 4：新增 Start Menu 快捷方式安装脚本

- 操作：在项目根目录新增文件 `install_start_menu_shortcut.ps1`。
- 文件职责：为当前 Windows 用户创建开始菜单快捷方式：
  - 快捷方式目录：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard`
  - 快捷方式文件：`RL-MEC Dashboard.lnk`
  - 目标程序：`%WINDIR%\System32\wscript.exe`
  - 参数：项目内 `start_dashboard.vbs` 的完整路径
  - 工作目录：项目根目录
- 脚本必须支持参数：
  - `param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)`
  - 默认安装到当前用户开始菜单。
  - 当传入 `-AllUsers` 时安装到公共开始菜单；该模式可能需要管理员权限。
- 脚本必须包含以下检查：
  - `$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path`
  - `$VbsPath = Join-Path $ProjectRoot "start_dashboard.vbs"`
  - 若 `start_dashboard.vbs` 不存在，`throw "start_dashboard.vbs not found: $VbsPath"`
- 脚本核心实现必须使用 COM 快捷方式 API：

  ```powershell
  $WshShell = New-Object -ComObject WScript.Shell
  $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
  $Shortcut.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
  $Shortcut.Arguments = "`"$VbsPath`""
  $Shortcut.WorkingDirectory = $ProjectRoot
  $Shortcut.Description = "Launch RL-MEC Dashboard"
  $Shortcut.Save()
  ```

- 目录创建必须使用：
  ```powershell
  New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null
  ```
- 结尾必须输出：
  ```powershell
  Write-Host "Created Start Menu shortcut: $ShortcutPath"
  ```
- 禁止：
  - 不要复制 `.bat`、`.vbs` 或 Python 文件到开始菜单目录。
  - 不要把仓库路径写死为 `C:\Users\22003\...`。
  - 不要修改 `start_dashboard.bat` 的启动参数。
  - 不要让快捷方式直接调用 `python.exe serve_dashboard.py`；必须复用 `start_dashboard.vbs`，避免重复维护路径和依赖检查逻辑。

**验证**：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
$Shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk"
if (!(Test-Path $Shortcut)) { throw "shortcut missing: $Shortcut" }
```

---

### [ADD] 模块 9 — Step 5：新增 Start Menu 快捷方式卸载脚本

- 操作：在项目根目录新增文件 `uninstall_start_menu_shortcut.ps1`。
- 文件职责：删除当前 Windows 用户的开始菜单快捷方式。
- 脚本必须支持参数：
  - `param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)`
  - 默认从当前用户开始菜单删除。
  - `-AllUsers` 从公共开始菜单删除。
- 目标路径必须与安装脚本完全一致：
  - `$ShortcutDir = Join-Path $ProgramsDir "RL-MEC Dashboard"`
  - `$ShortcutPath = Join-Path $ShortcutDir "$ShortcutName.lnk"`
- 删除逻辑：
  - 如果 `.lnk` 存在，删除它。
  - 如果 `RL-MEC Dashboard` 目录存在且已为空，删除目录。
  - 如果快捷方式不存在，不报错，只输出 `Shortcut not found: <path>`。
- 禁止：
  - 不要删除项目目录。
  - 不要删除 `start_dashboard.vbs` 或 `start_dashboard.bat`。
  - 不要清理 paper2 输出目录。

**关键代码指引**：

```powershell
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed Start Menu shortcut: $ShortcutPath"
} else {
    Write-Host "Shortcut not found: $ShortcutPath"
}

if (Test-Path $ShortcutDir) {
    $Remaining = Get-ChildItem -Path $ShortcutDir -Force
    if ($Remaining.Count -eq 0) {
        Remove-Item $ShortcutDir -Force
        Write-Host "Removed empty Start Menu folder: $ShortcutDir"
    }
}
```

**验证**：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
$Shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk"
if (Test-Path $Shortcut) { throw "shortcut still exists: $Shortcut" }
```

---

### [ADD] 模块 9 — Step 6：新增 Windows Start Menu 启动说明文档

- 操作：新增文件 `docs/windows-start-menu-launcher.md`。
- 文档结构必须包含：

  ```markdown
  # Windows Start Menu Launcher

  ## 目标
  ## 安装
  ## 启动
  ## 卸载
  ## 故障排查
  ## 为什么本轮不做浏览器扩展
  ```

- `## 目标` 必须说明：
  - 该功能只是简化 dashboard server 启动入口。
  - 不启动、不停止、不重启 paper2 训练任务。
- `## 安装` 必须给出：
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
  ```
- `## 启动` 必须说明：
  - 从 Windows 开始菜单搜索 `RL-MEC Dashboard`。
  - 启动后脚本会打开 `http://127.0.0.1:8088`。
- `## 卸载` 必须给出：
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
  ```
- `## 故障排查` 至少包含：
  - 找不到快捷方式：重新运行安装命令。
  - PowerShell execution policy 阻止：确认命令包含 `-ExecutionPolicy Bypass`。
  - 点击后浏览器打不开：手动访问 `http://127.0.0.1:8088`，并用 `start_dashboard.bat` 查看控制台日志。
  - Python 路径失效：检查 `start_dashboard.bat` 中 `PYTHON=` 是否仍指向 paper2 虚拟环境。
- `## 为什么本轮不做浏览器扩展` 必须说明：
  - 普通浏览器扩展不能直接启动本地 `.bat` / `.vbs`。
  - 真正的一键启动需要 Native Messaging Host 和系统注册表配置，维护成本高。
  - 当前 Start Menu 快捷方式能满足一键启动目标，复杂度更低。

**验证**：

```bash
python - <<'PY'
from pathlib import Path
text = Path("docs/windows-start-menu-launcher.md").read_text(encoding="utf-8")
for phrase in [
    "Windows Start Menu Launcher",
    "install_start_menu_shortcut.ps1",
    "uninstall_start_menu_shortcut.ps1",
    "http://127.0.0.1:8088",
    "Native Messaging Host",
]:
    assert phrase in text
PY
```

---

### [ADD] 模块 9 — Step 7：新增脚本静态回归测试

- 操作：新增文件 `tests/test_windows_start_menu_scripts.py`。
- 测试目标：在非 Windows CI 环境中也能验证脚本关键内容，避免直接执行 COM API。
- 必须新增以下测试函数：

  ```python
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[1]

  def test_install_start_menu_script_targets_wscript_and_vbs():
      text = (ROOT / "install_start_menu_shortcut.ps1").read_text(encoding="utf-8")
      assert "New-Object -ComObject WScript.Shell" in text
      assert "CreateShortcut" in text
      assert "wscript.exe" in text
      assert "start_dashboard.vbs" in text
      assert "WorkingDirectory" in text
      assert "Created Start Menu shortcut" in text

  def test_install_start_menu_script_has_no_hardcoded_user_path():
      text = (ROOT / "install_start_menu_shortcut.ps1").read_text(encoding="utf-8")
      assert "C:\\Users\\22003" not in text
      assert "paper2\\paper2" not in text

  def test_uninstall_start_menu_script_only_removes_shortcut():
      text = (ROOT / "uninstall_start_menu_shortcut.ps1").read_text(encoding="utf-8")
      assert "Remove-Item $ShortcutPath -Force" in text
      assert "start_dashboard.bat" not in text
      assert "start_dashboard.vbs" not in text
      assert "paper2" not in text
  ```

- 禁止：
  - 不要在 pytest 中实际运行 PowerShell。
  - 不要依赖 Windows-only COM 对象执行。
  - 不要访问用户真实 `%APPDATA%`。

**验证**：

```bash
python -m pytest tests/test_windows_start_menu_scripts.py -v
```

---

## 受影响但无需修改的模块

- `serve_dashboard.py`：现有入口已通过 `parse_cli_args()` 和 `create_app(config)` 启动；Start Menu 快捷方式复用 `start_dashboard.vbs`，无需改 server 入口。
- `dashboard/api.py`：API 不变。
- `dashboard/config.py`：CLI 参数不变。
- `monitor_dashboard.html`：前端不变。
- `start_dashboard.bat`：保留现有依赖检查、server 启动和浏览器打开逻辑。
- `start_dashboard.vbs`：保留现有静默调用 `.bat --hidden` 逻辑。

## 本轮明确不做

- 不开发浏览器扩展。
- 不添加 Native Messaging Host。
- 不写注册表。
- 不把 dashboard 打包为 `.exe`。
- 不改变 `Stop Dashboard Server` 行为。
- 不启动、不停止、不重启 paper2 训练任务。

## patch 自检

1. 每条 `[MODIFY]` 已标明原 Step 编号和原描述。
2. 每条 `[ADD]` 都具体到文件名、脚本参数、关键代码、验证命令。
3. 无 `[DELETE]` 操作。
4. 会影响已完成的模块 9，因此 Codex 执行后应在 `docs/progress.md` 中追加新增 Step，并将模块 9 Step 1 标记为 `[MODIFIED]`。
5. 不要求 Codex 在 patch 范围外重构启动脚本或后端代码。
6. 不要求用户安装浏览器扩展或改浏览器安全设置。

## 验收标准

- [ ] `install_start_menu_shortcut.ps1` 存在，并能创建当前用户 Start Menu 快捷方式。
- [ ] `uninstall_start_menu_shortcut.ps1` 存在，并能删除对应快捷方式。
- [ ] 快捷方式目标是 `wscript.exe`，参数指向项目内 `start_dashboard.vbs`。
- [ ] README 给出 Start Menu 推荐启动方式、安装命令和卸载命令。
- [ ] `docs/windows-start-menu-launcher.md` 解释安装、启动、卸载、故障排查和浏览器扩展暂缓原因。
- [ ] `python -m pytest tests/test_windows_start_menu_scripts.py -v` 通过。
- [ ] 原有 `start_dashboard.vbs` / `start_dashboard.bat` 启动方式仍可用。
- [ ] dashboard 仍只读训练输出，不控制 paper2 训练任务。
