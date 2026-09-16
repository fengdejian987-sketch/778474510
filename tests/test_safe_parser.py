import pytest
from src.core import safe_parser as sp

def test_basic_math():
    ok, info = sp.try_parse("m*c**2")
    assert ok
    # info should be a short string representation
    assert "c**2" in info or "c*c" in info or "m*c**2" in info

def test_numbers_and_ops():
    ok, info = sp.try_parse("3 * x + 4.5 / y")
    assert ok
    assert "3" in info

def test_disallowed_function_call():
    ok, info = sp.try_parse("__import__('os').system('ls')")
    assert not ok
    assert info in ("disallowed_token", "disallowed_node", "disallowed_name", "syntax_error", "parse_error")

def test_disallowed_attribute():
    ok, info = sp.try_parse("obj.__dict__")
    assert not ok
    assert info in ("disallowed_token", "disallowed_node", "disallowed_name", "parse_error")

def test_empty_and_invalid():
    ok, info = sp.try_parse("")
    assert not ok and info == "empty"
    ok2, info2 = sp.try_parse(None)
    assert not ok2 and info2 == "invalid_type"
