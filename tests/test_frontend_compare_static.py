from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_compare_displays_evidence_mixed_warning():
    html = HTML_PATH.read_text(encoding="utf-8")
    compare_panel = html.split('<section id="compare-panel"', 1)[1].split("</section>", 1)[0]
    render_compare_state = html.split("function renderCompareState()", 1)[1].split(
        "function renderCompareTable", 1
    )[0]

    assert 'id="compare-evidence-warning"' in compare_panel
    assert 'class="evidence-boundary-warning"' in compare_panel
    assert "payload.evidence_mixed" in render_compare_state
    assert "payload.warning" in render_compare_state
    assert "different evidence boundary" in compare_panel
