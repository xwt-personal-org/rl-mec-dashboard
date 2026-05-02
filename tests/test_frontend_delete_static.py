from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_contains_danger_zone_and_confirm_flow():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "danger-zone" in html
    assert "Danger Zone" in html
    assert "delete-targets" in html
    assert "delete-preview" in html
    assert "delete-confirm-input" in html
    assert "Delete Source Files" in html
    assert "previewDeleteTarget" in html
    assert "confirmDeleteTarget" in html
    assert "/api/delete-targets" in html
    assert "/api/delete-preview" in html
    assert "/api/delete-confirm" in html


def test_frontend_refreshes_runs_backups_and_delete_targets_after_confirm():
    html = HTML_PATH.read_text(encoding="utf-8")
    confirm_function = html.split("async function confirmDeleteTarget()", 1)[1].split("function renderRunOverview", 1)[0]

    assert "await loadRuns()" in confirm_function
    assert "await loadBackups()" in confirm_function
    assert "await loadBackupDiagnostics()" in confirm_function
    assert "await loadDeleteTargets()" in confirm_function
    assert "fetchInitialRunState" in confirm_function
