from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
REFERENCES_DIR = ROOT / "docs" / "references"

REQUIRED_DASHBOARD_MODULES = [
    "config",
    "models",
    "log_parser",
    "protocol_reader",
    "experiment_reader",
    "benchmark_schema",
    "run_discovery",
    "state_aggregator",
    "state_store",
    "api",
    "sse",
    "convergence",
    "delete_service",
    "exporter",
]

REQUIRED_API_ENDPOINTS = [
    "/api/health",
    "/api/runs/{run_id}/convergence",
    "/api/backups/{backup_id}/convergence",
    "/api/delete-targets",
    "/api/delete-preview",
    "/api/delete-confirm",
    "/api/compare",
    "/api/export/results.csv",
    "/api/export/results.md",
]


def test_agents_lists_current_modules_endpoints_and_test_commands():
    agents = AGENTS.read_text(encoding="utf-8")

    for module in REQUIRED_DASHBOARD_MODULES:
        assert f"`{module}.py`" in agents

    for endpoint in REQUIRED_API_ENDPOINTS:
        assert endpoint in agents

    assert "python -m pytest -v" in agents
    assert "python -m pytest tests/test_api.py tests/test_api_convergence.py tests/test_api_delete.py -v" in agents
    assert "python -m pytest tests/test_docs_contract_static.py -v" in agents


def test_reference_docs_surface_is_declared_and_present():
    readme = README.read_text(encoding="utf-8")
    architecture = ARCHITECTURE.read_text(encoding="utf-8")

    assert REFERENCES_DIR.exists()
    assert any(REFERENCES_DIR.glob("*.md"))
    assert "docs/references/" in readme
    assert "No root `ref/` directory" in readme
    assert "`ref/architecture-brief.md` Linear reference maps to `docs/architecture.md`" in architecture


def test_architecture_dependency_graph_covers_dashboard_modules():
    architecture = ARCHITECTURE.read_text(encoding="utf-8")

    assert "Current module dependency graph" in architecture
    for module in REQUIRED_DASHBOARD_MODULES:
        assert f"dashboard.{module}" in architecture
