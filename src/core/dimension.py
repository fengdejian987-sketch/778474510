import re
from typing import Dict

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
        """Parse a simple expression and return combined dimension as a dict.

        For unsupported symbols, it will skip them but include a note in returned dict
        by adding a special key `_unknown_symbols` listing them.
        """
        expr = expression.replace(' ', '')
        # split by * or / while keeping powers
        tokens = re.split(r'(?<!\*)[*/]', expr)
        result = {}
        unknown = set()

        for token in tokens:
            # handle parentheses by stripping them for now
            token = token.strip('()')
            m = self._symbol_regex.match(token)
            if not m:
                # try to extract symbol and power via simple patterns
                # if fails, mark unknown
                unknown.add(token)
                continue
            symbol = m.group(1)
            power = int(m.group(3)) if m.group(3) else 1

            base = self._base_map.get(symbol)
            if base is None:
                unknown.add(symbol)
                continue
            for k, v in base.items():
                result[k] = result.get(k, 0) + v * power

        if unknown:
            result['_unknown_symbols'] = list(sorted(unknown))
        return result
