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
