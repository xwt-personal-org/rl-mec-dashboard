"""Tests for legacy dashboard log parsing."""

from dashboard.log_parser import (
    classify_log_line,
    parse_algo_switch,
    parse_algorithm_count_from_summary,
    parse_benchmark_summary,
    parse_elapsed_from_tqdm,
    parse_env_from_algo_header,
    parse_eta_from_tqdm,
    parse_log_line,
    parse_result,
    parse_step_from_tqdm,
    parse_update_count,
    strip_log_prefix,
)


def test_strip_log_prefix_cases():
    assert (
        strip_log_prefix("2026-04-23 10:15:41,123 - INFO - Algorithm: GRPO")
        == "Algorithm: GRPO"
    )
    assert strip_log_prefix("Algorithm: GRPO") == "Algorithm: GRPO"


def test_parse_step_from_tqdm_standard():
    line = "Training GRPOAgent:   0%|          | 0/500000 [00:00<04:44, 1751.99it/s]"

    assert parse_step_from_tqdm(line) == (0, 500000, 1751.99)
    assert parse_eta_from_tqdm(line) == 284


def test_parse_step_from_tqdm_elapsed_only():
    line = "Training GRPOAgent: 501760it [3:20:45, 47.30it/s, update_count=481436.000]"

    assert parse_step_from_tqdm(line) == (501760, 0, 47.30)


def test_parse_result_standard():
    result = parse_result("[GRPO] reward=11.8355+/-1.0085  time=325.8s")

    assert result is not None
    assert result.algorithm == "GRPO"
    assert result.reward == 11.8355
    assert result.reward_std == 1.0085
    assert result.train_time == 325.8
    assert result.source == "log"
    assert result.status == "finished"


def test_parse_result_fallback():
    result = parse_result("[GRPO] some text reward=11.0 time=325s")

    assert result is not None
    assert result.algorithm == "GRPO"
    assert result.reward == 11.0
    assert result.reward_std == 0
    assert result.train_time == 325.0


def test_parse_algo_switch():
    assert parse_algo_switch("Algorithm: GRPO") == "GRPO"


def test_parse_update_count():
    assert parse_update_count("update_count=481436.000") == 481436


def test_parse_env_from_algo_header():
    assert parse_env_from_algo_header("Env: local") == "local"


def test_parse_benchmark_summary():
    assert parse_benchmark_summary("ALL ALGORITHMS COMPLETE") is True
    assert parse_benchmark_summary("Benchmark finished") is True


def test_parse_algorithm_count_from_summary():
    assert parse_algorithm_count_from_summary("BENCHMARK -- Full Benchmark (17 algorithms)") == 17


def test_parse_elapsed_from_tqdm():
    assert parse_elapsed_from_tqdm("Training GRPOAgent: 3%| | 3/100 [01:02:03<02:03:04, 1.0it/s]") == 3723


def test_parse_log_line_algorithm_started():
    events = parse_log_line("Algorithm: GRPO", source_file="benchmark.log")

    assert {"type": "algorithm_started", "algorithm": "GRPO", "source_file": "benchmark.log"} in events


def test_parse_log_line_algorithm_finished():
    events = parse_log_line("[GRPO] reward=11.8355+/-1.0085  time=325.8s")

    assert any(event["type"] == "algorithm_finished" and event["algorithm"] == "GRPO" for event in events)


def test_classify_log_line_false_saveraerror():
    assert classify_log_line("saveraerror") is None


def test_classify_log_line_false_warninglight():
    assert classify_log_line("warninglight") is None


def test_classify_log_line_false_algorithmically():
    assert classify_log_line("algorithmically") is None


def test_classify_log_line_false_completely():
    assert classify_log_line("completely") is None


def test_classify_log_line_true_error():
    assert classify_log_line("Error IPPO seed=42: unexpected keyword argument") == "error"


def test_classify_log_line_true_warn():
    assert classify_log_line("WARNING: high memory usage") == "warn"


def test_classify_log_line_true_info():
    assert classify_log_line("Algorithm: GRPO") == "info"
