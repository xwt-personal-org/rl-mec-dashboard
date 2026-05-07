from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_contains_convergence_panel_and_chart():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "convergence-panel" in html
    assert "convergence.title" in html
    assert "convergence-metric" in html
    assert "convergence-algorithm-tabs" in html
    assert "convergenceChart" in html
    assert "Refresh Convergence" in html
    assert "renderConvergenceChart" in html
    assert "selectConvergenceAlgorithm" in html


def test_frontend_has_convergence_endpoint_switch_for_backup_and_run():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "currentConvergenceEndpoint" in html
    assert "'/api/runs/' + encodeURIComponent(runId) + '/convergence'" in html
    assert "'/api/backups/' + encodeURIComponent(runId) + '/convergence'" in html
    assert "dashboardState.currentSelectionType === 'backup'" in html
    assert "currentSelectionType" in html


def test_frontend_loads_convergence_after_run_selection():
    html = HTML_PATH.read_text(encoding="utf-8")
    select_function = html.split("async function selectRun(value)", 1)[1].split("function toggleCompareRun", 1)[0]
    startup_function = html.split("document.addEventListener('DOMContentLoaded'", 1)[1]

    assert "await fetchInitialRunState(selection.value)" in select_function
    assert "await loadConvergence()" in select_function
    assert "await fetchInitialRunState(dashboardState.currentSelectionValue)" in startup_function
    assert "await loadConvergence()" in startup_function


def test_frontend_clears_convergence_after_delete_confirm():
    html = HTML_PATH.read_text(encoding="utf-8")
    confirm_function = html.split("async function confirmDeleteTarget()", 1)[1].split("async function loadCompareData", 1)[0]

    assert "dashboardState.convergencePayload = null" in confirm_function
    assert "dashboardState.selectedConvergenceAlgorithm = \"\"" in confirm_function
    assert "destroyConvergenceChart()" in confirm_function
    assert "await loadConvergence()" in confirm_function
