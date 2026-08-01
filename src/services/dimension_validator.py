from typing import Dict
from src.core.dimension import DimensionParser

class DimensionValidator:
    def __init__(self):
        self.parser = DimensionParser()

    def validate_formula(self, formula_str: str) -> Dict:
        try:
            if '=' in formula_str:
                left, right = formula_str.split('=')
            else:
                return {'is_valid': False, 'error': 'no equality in formula'}
            left_dim = self.parser.parse_dimension(left.strip())
            right_dim = self.parser.parse_dimension(right.strip())
            is_valid = {k: v for k, v in left_dim.items() if k != '_unknown_symbols'} == {k: v for k, v in right_dim.items() if k != '_unknown_symbols'}
            return {
                'is_valid': is_valid,
                'left_dimension': left_dim,
                'right_dimension': right_dim,
                'match_percentage': 100 if is_valid else 0,
                'details': {
                    'left_unknown': left_dim.get('_unknown_symbols', []),
                    'right_unknown': right_dim.get('_unknown_symbols', [])
                }
            }
        except Exception as e:
            return {'is_valid': False, 'error': str(e)}
