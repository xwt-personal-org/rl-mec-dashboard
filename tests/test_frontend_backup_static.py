from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_backup_strings_are_present():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "backup.title" in html
    assert "loadRunBackups" in html
    assert "/api/runs/${runId}/backups" in html


def test_frontend_backup_panel_is_read_only():
    html = HTML_PATH.read_text(encoding="utf-8")
    backup_section = html.split('data-i18n="backup.title"', 1)[1].split('data-i18n="table.algorithmStatus"', 1)[0]

    assert "restore" not in backup_section.lower()
    assert "delete" not in backup_section.lower()
    assert "fresh" not in backup_section.lower()


def test_frontend_contains_global_backup_diagnostics_ui():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "global-backups" in html
    assert "backup-diagnostics" in html
    assert "loadBackupDiagnostics" in html
    assert "renderGlobalBackups" in html
    assert "renderBackupDiagnostics" in html
    assert "/api/backups/diagnostics" in html


def test_frontend_can_select_backups_as_dashboard_options():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert 'value="backup:' in html
    assert "currentSelectionType" in html
    assert "parseSelection" in html
    assert "/api/backups/' + encodeURIComponent(selection.id)" in html
    assert "selectRun(\\'backup:" in html or "selectRun('backup:" in html
    assert "/api/backups/' + encodeURIComponent(runId) + '/logs/" in html
