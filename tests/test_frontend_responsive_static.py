from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_frontend_uses_design_breakpoint_page_padding():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "--page-padding: 24px;" in html
    assert "@media (max-width: 1100px)" in html
    tablet_block = html.split("@media (max-width: 1100px)", 1)[1].split("@media (max-width: 768px)", 1)[0]
    mobile_block = html.split("@media (max-width: 768px)", 1)[1].split("@media (max-width: 480px)", 1)[0]

    assert "--page-padding: 14px;" in tablet_block
    assert "--page-padding: 10px;" in mobile_block
    assert ".workspace {" in html
    assert "padding: var(--page-padding);" in html


def test_frontend_mobile_card_grids_stack_without_changing_controls():
    html = HTML_PATH.read_text(encoding="utf-8")
    mobile_block = html.split("@media (max-width: 768px)", 1)[1].split("@media (max-width: 480px)", 1)[0]

    assert ".status-bar { grid-template-columns: 1fr; }" in mobile_block
    assert ".run-overview { grid-template-columns: 1fr;" in mobile_block
    assert ".backup-grid, .diagnostics-grid { grid-template-columns: 1fr; }" in mobile_block
    assert ".topbar, .filters, .compare-controls, .convergence-controls, .log-controls { align-items: stretch; }" in mobile_block


def test_frontend_tables_scroll_horizontally_without_compressing_labels():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert ".table-wrap { overflow-x: auto;" in html
    assert "th, td { border-bottom: 1px solid var(--outline-soft);" in html
    assert "white-space: nowrap;" in html
