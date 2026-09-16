import multiprocessing
import time
import pytest
from src.core import safe_parser

def _invoke_in_process(expr, q):
    # Run safe_parser.try_parse in a separate process to simulate isolation
    try:
        ok, info = safe_parser.try_parse(expr)
        q.put((ok, info))
    except Exception as e:
        q.put((False, "exception"))

def run_in_worker(expr, timeout=2):
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue(1)
    p = ctx.Process(target=_invoke_in_process, args=(expr, q))
    p.start()
    try:
        ok, info = q.get(timeout=timeout)
    except Exception:
        p.terminate()
        p.join(timeout=0.5)
        return False, "timeout"
    finally:
        if p.is_alive():
            p.terminate()
            p.join(timeout=0.5)
    return ok, info

def test_long_input_rejected():
    expr = "1" + "*1" * 10000  # likely exceed MAX_EXPR_LENGTH or node count
    ok, info = run_in_worker(expr, timeout=3)
    assert not ok
    assert info in ("too_long","too_many_nodes","parse_error","syntax_error")

def test_deep_nesting_rejected():
    # build deep nesting
    depth = safe_parser.MAX_AST_DEPTH + 10
    expr = "1"
    for _ in range(depth):
        expr = f"({expr})"
    ok, info = run_in_worker(expr, timeout=3)
    assert not ok
    assert info in ("ast_too_deep","too_many_nodes","parse_error","syntax_error")
