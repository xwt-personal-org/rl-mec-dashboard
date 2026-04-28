from dashboard.log_parser import parse_algo_switch, parse_result


def test_legacy_parser_imports_work():
    assert parse_algo_switch("Algorithm: GRPO") == "GRPO"
    assert parse_result("[GRPO] reward=1.0+/-0.1  time=2.0s") is not None
