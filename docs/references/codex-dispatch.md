## 类型：patch

# Codex 任务派发

进入增量合并模式（patch）。本次只处理 Windows Start Menu 一键启动入口，不重跑既有完整计划。

## 目标仓库

- 仓库：`w2030298-art/rl-mec-dashboard`
- 分支：`master`
- 变更目标：让用户可以通过 Windows 开始菜单一键启动 RL-MEC Dashboard
- 关键约束：dashboard 仍只读训练输出，不启动、不停止、不重启 paper2 训练任务
- 本轮不做：浏览器扩展、Native Messaging Host、注册表配置、`.exe` 打包、后端重构

## 启动

1. 读取 `docs/plan.md`，作为原计划基线。
2. 读取 `docs/progress.md`，确认当前状态为全部模块完成。
3. 读取 `docs/plan-patch.md`，本次必须严格按其中操作清单执行。
4. 检查现有文件：
   - `README.md`
   - `start_dashboard.bat`
   - `start_dashboard.vbs`
   - `serve_dashboard.py`
5. 不读取或修改 paper2 训练输出目录。

## 本次 patch 范围

只处理 `docs/plan-patch.md` 中以下条目：

1. `[MODIFY] 模块 9 — Step 1：更新 README`
2. `[ADD] 模块 9 — Step 4：新增 Start Menu 快捷方式安装脚本`
3. `[ADD] 模块 9 — Step 5：新增 Start Menu 快捷方式卸载脚本`
4. `[ADD] 模块 9 — Step 6：新增 Windows Start Menu 启动说明文档`
5. `[ADD] 模块 9 — Step 7：新增脚本静态回归测试`

## 执行规则

### [MODIFY] 标签

- 定位 `docs/plan.md` 中模块 9 Step 1。
- 检查 `docs/progress.md`：该 Step 已完成时，按 patch 中“修改后”内容更新对应文件。
- 本次修改目标文件：
  - `README.md`
- 完成后：
  - 在 `docs/progress.md` 中将模块 9 Step 1 标注为 `[MODIFIED]`，并保留已完成状态。
  - 不删除原有启动方式说明。

### [ADD] 标签

- 按 `docs/plan-patch.md` 中每个新增 Step 的定义创建文件。
- 本次新增目标文件：
  - `install_start_menu_shortcut.ps1`
  - `uninstall_start_menu_shortcut.ps1`
  - `docs/windows-start-menu-launcher.md`
  - `tests/test_windows_start_menu_scripts.py`
- 完成后：
  - 在 `docs/progress.md` 的模块 9 下追加 Step 4、Step 5、Step 6、Step 7。
  - 每个新增 Step 标注为 `[ADDED]`，验证通过后勾选完成。

### 通用规则

- 每完成一个 `[MODIFY]` 或 `[ADD]` 项，立即运行该项验证命令。
- 验证通过后继续下一项，不要停下来询问。
- 验证失败时自行诊断并修复，最多重试 2 次。
- 重试 2 次仍失败时：
  - 在 `docs/issues.md` 追加失败记录。
  - 停下并报告失败原因、已修改文件、验证输出。
- 不重跑 `docs/plan.md` 中未被 patch 涉及的步骤。
- 不在 patch 范围外“顺手”重构其他模块。

## 文件实现要求

### 1. `install_start_menu_shortcut.ps1`

必须满足：

- 默认安装到当前用户开始菜单：
  - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk`
- 支持：
  ```powershell
  param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)
  ```
- 目标必须是：
  - `wscript.exe`
- 参数必须指向：
  - 当前项目目录下的 `start_dashboard.vbs`
- 工作目录必须是项目根目录。
- 必须检查 `start_dashboard.vbs` 是否存在，不存在则 `throw`。
- 必须使用 `New-Object -ComObject WScript.Shell` 和 `CreateShortcut()`。
- 不得写死 `C:\Users\22003\...`。
- 不得直接调用 `python.exe serve_dashboard.py`。
- 不得复制项目文件到开始菜单目录。

### 2. `uninstall_start_menu_shortcut.ps1`

必须满足：

- 默认删除当前用户开始菜单中的：
  - `RL-MEC Dashboard\RL-MEC Dashboard.lnk`
- 支持：
  ```powershell
  param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)
  ```
- 如果快捷方式不存在，不报错。
- 仅删除 `.lnk` 和空的 `RL-MEC Dashboard` 开始菜单目录。
- 不得删除项目目录。
- 不得删除 `start_dashboard.vbs`、`start_dashboard.bat` 或 paper2 输出目录。

### 3. `docs/windows-start-menu-launcher.md`

必须包含以下一级或二级标题：

```markdown
# Windows Start Menu Launcher

## 目标
## 安装
## 启动
## 卸载
## 故障排查
## 为什么本轮不做浏览器扩展
```

必须说明：

- 该功能只简化 dashboard server 启动入口。
- 不启动、不停止、不重启 paper2 训练任务。
- 安装命令：
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
  ```
- 卸载命令：
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
  ```
- 浏览器扩展暂缓原因：
  - 普通扩展不能直接启动本地 `.bat` / `.vbs`
  - 真正一键启动需要 Native Messaging Host 和系统注册表配置
  - Start Menu 快捷方式复杂度更低

### 4. `tests/test_windows_start_menu_scripts.py`

必须是静态测试，不实际运行 PowerShell，不访问真实 `%APPDATA%`。

至少包含：

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

可在不削弱上述断言的基础上增加测试。

## 验证命令

按顺序运行：

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

```bash
python -m pytest tests/test_windows_start_menu_scripts.py -v
```

在 Windows 本机可额外运行手工验证：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_start_menu_shortcut.ps1
$Shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk"
if (!(Test-Path $Shortcut)) { throw "shortcut missing: $Shortcut" }
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall_start_menu_shortcut.ps1
$Shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\RL-MEC Dashboard\RL-MEC Dashboard.lnk"
if (Test-Path $Shortcut) { throw "shortcut still exists: $Shortcut" }
```

## 仅以下情况停下

- 验证失败且重试 2 次仍无法解决。
- `start_dashboard.vbs` 或 `start_dashboard.bat` 缺失，导致无法安全复用现有启动链路。
- patch 执行中发现必须修改后端启动逻辑或 paper2 路径配置。
- 需要浏览器扩展、Native Messaging Host 或注册表配置才能满足需求。
- 需要用户提供管理员权限才能完成当前用户级 Start Menu 快捷方式安装。

## 禁止行为

- 不要全量重跑 `docs/plan.md` 中已完成的模块。
- 不要修改 dashboard API、前端页面逻辑或后端状态聚合逻辑。
- 不要修改 `serve_dashboard.py`。
- 不要修改 `start_dashboard.bat` 的 Python 路径或启动参数。
- 不要修改 `start_dashboard.vbs`。
- 不要引入第三方依赖。
- 不要创建浏览器扩展目录。
- 不要写注册表。
- 不要打包 `.exe`。
- 不要删除或清理 paper2 输出文件。
- 不要把 dashboard 改成可控制训练任务的工具。

## 完成后

输出完成报告，必须包含：

1. 已处理的 `[MODIFY]` / `[ADD]` 列表。
2. 新增和修改的文件清单。
3. 每条验证命令的结果。
4. `docs/progress.md` 更新摘要。
5. `docs/issues.md` 是否新增记录。
6. 明确说明：
   - Windows Start Menu 入口已可安装。
   - 现有 `.vbs` / `.bat` 入口仍保留。
   - dashboard 仍只读，不控制 paper2 训练任务。

现在开始执行。
