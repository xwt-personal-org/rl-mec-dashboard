from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_contains_mainline_a_diagnostics_panel():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "mainline-a-diagnostics" in html
    assert "loadMainlineADiagnostics" in html
    assert "renderMainlineADiagnostics" in html
    assert "/api/mainline-a/diagnostics" in html


def test_mainline_a_diagnostics_panel_surfaces_required_fields():
    html = HTML_PATH.read_text(encoding="utf-8")

    panel = html.split('id="mainline-a-diagnostics"', 1)[1].split(
        'id="danger-section"',
        1,
    )[0]
    renderer = html.split("function renderMainlineADiagnostics", 1)[1].split(
        "function renderDeleteTargets",
        1,
    )[0]

    assert "mainline.title" in panel
    assert "mainline.description" in panel
    assert "mainline.paper2Root" in renderer
    assert "mainline.benchmarkFiles" in renderer
    assert "mainline.launchJson" in renderer
    assert "paper2_root" in renderer
    assert "benchmark_files" in renderer
    assert "launch_json" in renderer
