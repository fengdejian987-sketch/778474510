import re
from typing import Dict
from functools import lru_cache

class DimensionParser:
    """
    Minimal dimension parser for demonstration.

    It supports expressions that are products and powers of known quantity symbols,
    e.g. 'm * c**2' or 'F * v' where known symbol -> base dimension mapping exists.

    This is NOT a complete dimensional analysis engine but a practical starting point.
    """

    # base dimensions: M (mass), L (length), T (time)
    _base_map = {
        'm': {'M': 1},      # mass
        'v': {'L': 1, 'T': -1},  # velocity
        'u': {'L': 1, 'T': -1},
        'a': {'L': 1, 'T': -2},  # acceleration
        'F': {'M': 1, 'L': 1, 'T': -2},  # force
        'E': {'M': 1, 'L': 2, 'T': -2},
        'c': {'L': 1, 'T': -1},  # speed of light treated as velocity
        'P': {'M': 1, 'L': -1, 'T': -2},
        # add more as needed
    }

    _symbol_regex = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(\*\*\s*([-+]?\d+))?")

    def parse_dimension(self, expression: str) -> Dict[str, int]:
        """Wrapper: calls cached internal parser and returns a fresh dict copy."""
        res = self._parse_dimension_cached(expression)
        # return a shallow copy to avoid callers mutating cached dicts
        return dict(res)

    @staticmethod
    @lru_cache(maxsize=4096)
    def _parse_dimension_cached(expression: str) -> Dict[str, int]:
        expr = (expression or "").replace(' ', '')
        tokens = re.split(r'(?<!\*)[*/]', expr)
        result = {}
        unknown = set()

        for token in tokens:
            token = token.strip('()')
            m = DimensionParser._symbol_regex.match(token)
            if not m:
                unknown.add(token)
                continue
            symbol = m.group(1)
            power = int(m.group(3)) if m.group(3) else 1

            base = DimensionParser._base_map.get(symbol)
            if base is None:
                unknown.add(symbol)
                continue
            for k, v in base.items():
                result[k] = result.get(k, 0) + v * power

        if unknown:
            result['_unknown_symbols'] = list(sorted(unknown))
        return result
