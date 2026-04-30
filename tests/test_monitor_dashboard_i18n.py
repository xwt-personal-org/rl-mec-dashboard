import re
from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[1] / "monitor_dashboard.html"


def test_monitor_dashboard_static_i18n_keys_are_defined():
    html = HTML_PATH.read_text(encoding="utf-8")
    keys = set(re.findall(r'data-i18n(?:-[\w-]+)?="([^"]+)"', html))

    assert keys
    assert 'data-lang="zh"' in html
    assert 'data-lang="en"' in html

    english_block = html.split("en: {", 1)[1].split("},\n            zh:", 1)[0]
    chinese_block = html.split("zh: {", 1)[1].split("\n            }\n        };", 1)[0]

    for key in sorted(keys):
        assert f"'{key}':" in english_block
        assert f"'{key}':" in chinese_block


def test_monitor_dashboard_language_switch_persists_choice():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "const I18N_STORAGE_KEY = 'rl-mec-dashboard-language';" in html
    assert "function setLanguage(language)" in html
    assert "localStorage.setItem(I18N_STORAGE_KEY, language)" in html
    assert "document.documentElement.lang" in html
