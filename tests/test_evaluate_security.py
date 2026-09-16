import pytest
from evaluate.evaluate import safe_parse


def test_safe_parse_simple():
    ok, info = safe_parse("m * c**2", timeout=1.0)
    assert ok
    assert isinstance(info, str)


def test_safe_parse_timeout_or_error():
    # craft a deeply nested expression likely to cause timeout or parsing error
    long_expr = "x" + "**(" * 200 + "2" + ")" * 200
    ok, info = safe_parse(long_expr, timeout=0.5)
    assert not ok
    assert isinstance(info, str)
