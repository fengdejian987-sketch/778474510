"""Constrained decoding utilities.

This module provides a simple prefix_allowed_tokens_fn generator that can be used
with transformers' generate() to apply lightweight syntactic constraints during
decoding (e.g., preferring operators after operands, ensuring balanced parentheses
heuristics, and limiting tokens to a small operator/variable set where appropriate).

Note: A production-grade constrained decoder requires grammar or FSM-based control
and careful tokenizer vocab analysis. This implementation is a pragmatic, easy-to-deploy
starter that improves syntax for structured outputs like formulas.
"""

from typing import Callable, List, Set


def make_prefix_allowed_fn(tokenizer, operator_tokens: List[str] = None, variable_tokens: List[str] = None) -> Callable:
    """Return a prefix_allowed_tokens_fn to use with model.generate().

    The function inspects the last decoded token (as text) and returns a list of
    allowed token ids for the next step. This is heuristic-based and intended to
    reduce obvious syntax errors in formula generation.
    """
    if operator_tokens is None:
        # common operators and punctuation used in formulas
        operator_tokens = ['+', '-', '*', '/', '**', '(', ')', '=', '^']
    # map operator tokens to ids (if token not in vocab, ignore)
    op_token_ids = set()
    for t in operator_tokens:
        try:
            op_token_ids.add(tokenizer.convert_tokens_to_ids(t))
        except Exception:
            # some tokenizers don't have token directly; fallback later
            pass

    # prepare variable token ids heuristically: alphanumeric single-letter tokens if present
    var_token_ids = set()
    if variable_tokens:
        for v in variable_tokens:
            try:
                var_token_ids.add(tokenizer.convert_tokens_to_ids(v))
            except Exception:
                pass
    else:
        # try common single-letter variables and common multi-letter like 'mass'
        for v in list('abcdefghijklmnopqrstuvwxyz') + ['mass', 'velocity', 'time', 'c']:
            try:
                var_token_ids.add(tokenizer.convert_tokens_to_ids(v))
            except Exception:
                pass

    # safe default: allow operators + variable tokens + numbers
    # build a set of number-like token ids by checking tokens that are digits
    number_token_ids = set()
    for i in range(10):
        tok = str(i)
        try:
            number_token_ids.add(tokenizer.convert_tokens_to_ids(tok))
        except Exception:
            pass

    allowed_base = op_token_ids.union(var_token_ids).union(number_token_ids)

    def prefix_allowed_tokens_fn(batch_id: int, input_ids):
        # input_ids is a Tensor or list of token ids for the partially generated sequence
        if len(input_ids) == 0:
            # at start, allow variables and numbers and '('
            return list(allowed_base)
        last_id = int(input_ids[-1])
        # heuristics: if last token is operator, next should be variable/number/'(' or unary operator
        if last_id in op_token_ids:
            return list(var_token_ids.union(number_token_ids).union(set(tokenizer.convert_tokens_to_ids(['(')) if tokenizer.convert_tokens_to_ids(['(') else set())))
        # if last token is a variable or number, allow operator or ) or end
        if last_id in var_token_ids or last_id in number_token_ids:
            return list(op_token_ids.union(set([tokenizer.eos_token_id]) if hasattr(tokenizer, 'eos_token_id') else set()))
        # default fallback: allow base set
        return list(allowed_base)

    return prefix_allowed_tokens_fn
