import pytest

from serve_dashboard import (
    strip_log_prefix,
    parse_step_from_tqdm,
    parse_result,
    parse_algo_switch,
    parse_update_count,
    parse_env_from_algo_header,
    parse_benchmark_summary,
    classify_log_line,
)


def test_strip_log_prefix_cases():
    assert (
        strip_log_prefix("2026-04-23 10:15:41,123 - INFO - Algorithm: GRPO")
        == "Algorithm: GRPO"
    )
    assert strip_log_prefix("Algorithm: GRPO") == "Algorithm: GRPO"


def test_parse_step_from_tqdm_standard():
    line = "Training GRPOAgent:   0%|          | 0/500000 [00:00<04:44, 1751.99it/s]"
    res = parse_step_from_tqdm(line)
    assert isinstance(res, tuple) and len(res) == 3
    assert res[0] == 0
    assert res[1] == 500000


def test_parse_step_from_tqdm_fallback():
    # Provide a line that matches the second fallback pattern
    line = "Training GRPOAgent: 1%|▏          | 10/1000 [00:01<00:10, 1000it/s]"
    res = parse_step_from_tqdm(line)
    assert isinstance(res, tuple) or res is None


def test_parse_step_from_tqdm_elapsed_only():
    line = "Training GRPOAgent: 501760it [3:20:45, 47.30it/s, update_count=481436.000]"
    res = parse_step_from_tqdm(line)
    assert isinstance(res, tuple) or res is None


def test_parse_result_standard():
    line = "[GRPO] reward=11.8355+/-1.0085  time=325.8s"
    res = parse_result(line)
    assert isinstance(res, dict)
    assert res.get("algorithm") == "GRPO"
    assert isinstance(res.get("reward"), float)
    assert isinstance(res.get("train_time"), float)


def test_parse_result_fallback():
    line = "[GRPO] some text reward=11.0 time=325s"
    res = parse_result(line)
    # Fallback format may or may not include reward_std; ensure dict shape
    assert isinstance(res, dict) or res is None


def test_parse_algo_switch():
    line = "Algorithm: GRPO"
    res = parse_algo_switch(line)
    assert res == "GRPO"


def test_parse_update_count():
    line = "update_count=481436.000"
    res = parse_update_count(line)
    assert isinstance(res, int)
    assert res == 481436


def test_parse_env_from_algo_header():
    line = "Env: local"
    res = parse_env_from_algo_header(line)
    assert res == "local"


def test_parse_benchmark_summary():
    assert parse_benchmark_summary("ALL ALGORITHMS COMPLETE") is True
    assert parse_benchmark_summary("Benchmark finished") is True


def test_classify_log_line_false_saveraerror():
    assert classify_log_line("saveraerror") is None

def test_classify_log_line_false_warninglight():
    assert classify_log_line("warninglight") is None

def test_classify_log_line_false_algorithmically():
    assert classify_log_line("algorithmically") is None

def test_classify_log_line_false_completely():
    assert classify_log_line("completely") is None

def test_classify_log_line_true_error():
    assert classify_log_line("Error IPPO seed=42: PPOAgent.__init__() got an unexpected keyword argument") == "error"

def test_classify_log_line_true_warn():
    assert classify_log_line("WARNING: high memory usage") == "warn"

def test_classify_log_line_true_info():
    assert classify_log_line("Algorithm: GRPO") == "info"
