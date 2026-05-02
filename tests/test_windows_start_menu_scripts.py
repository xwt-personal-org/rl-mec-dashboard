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


def test_scripts_share_shortcut_parameters():
    install_text = (ROOT / "install_start_menu_shortcut.ps1").read_text(encoding="utf-8")
    uninstall_text = (ROOT / "uninstall_start_menu_shortcut.ps1").read_text(encoding="utf-8")
    expected_param = 'param([string]$ShortcutName = "RL-MEC Dashboard", [switch]$AllUsers)'
    assert expected_param in install_text
    assert expected_param in uninstall_text
    assert 'Join-Path $ShortcutDir "$ShortcutName.lnk"' in install_text
    assert 'Join-Path $ShortcutDir "$ShortcutName.lnk"' in uninstall_text
