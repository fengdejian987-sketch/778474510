from typing import Optional, Dict
from src.core.formula import Formula
import sympy as sp

class UnifiedFormulaLibrary:
    """Lightweight unified formula library using sympy for symbolic ops."""

    def __init__(self, db_session: Optional[object] = None):
        self.session = db_session
        self._store = {}

    def create_formula(self, id: str, name_zh: str, formula_str: str, latex_str: str = "") -> Formula:
        f = Formula(id=id, name_zh=name_zh, formula_str=formula_str, latex_str=latex_str)
        self._store[id] = f
        return f

    def get_formula(self, formula_id: str) -> Formula:
        return self._store.get(formula_id)

    def derive_formula(self, formula_id: str, var: str) -> str:
        formula = self.get_formula(formula_id)
        if not formula:
            raise ValueError("formula not found")
        expr = sp.sympify(formula.formula_str.replace('=', '-(') + ')') if '=' in formula.formula_str else sp.sympify(formula.formula_str)
        sym = sp.symbols(var)
        result = sp.diff(expr, sym)
        return str(result)

    def list_formulas(self):
        return list(self._store.values())
