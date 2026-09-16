# 安全解析器：用 AST 白名单解析表达式并构建 sympy 表达式（不直接 eval / 不用 parse_expr）
import ast
import re
from typing import Tuple, Optional
import sympy as sp

# Limits (可按需在 CI/部署时配置为环境变量)
MAX_EXPR_LENGTH = 2000
MAX_NODE_COUNT = 2000
MAX_AST_DEPTH = 100
ALLOWED_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Disallowed substrings (快速拒绝常见攻击向量)
DISALLOWED_SUBSTRINGS = ["__import__", "import ", "os.", "sys.", "eval(", "exec(", "subprocess", "open(", "lambda ", "getattr("]

class ParseError(Exception):
    code: str
    details: Optional[str]

    def __init__(self, code: str, details: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.details = details

def _check_disallowed_substrings(s: str) -> None:
    low = s.lower()
    for bad in DISALLOWED_SUBSTRINGS:
        if bad in low:
            raise ParseError("disallowed_token", bad)

def _count_and_check_ast(node: ast.AST, depth: int = 0, counter: Optional[dict] = None) -> int:
    """Traverse AST, ensure only allowed node types and count nodes and depth."""
    if counter is None:
        counter = {"count": 0, "max_depth": 0}

    counter["count"] += 1
    counter["max_depth"] = max(counter["max_depth"], depth)
    if counter["count"] > MAX_NODE_COUNT:
        raise ParseError("too_many_nodes", str(counter["count"]))
    if counter["max_depth"] > MAX_AST_DEPTH:
        raise ParseError("ast_too_deep", str(counter["max_depth"]))

    # Allowed node classes
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
        ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
        ast.Mod, ast.USub, ast.UAdd, ast.BitXor, ast.FloorDiv, ast.Subscript,
        ast.Index, ast.Tuple, ast.List, ast.UnaryOp, ast.Attribute, ast.Call
    )
    # We'll whitelist structural nodes more carefully below; disallow Call/Attribute explicitly
    if isinstance(node, ast.Call):
        raise ParseError("disallowed_node", "Call")
    if isinstance(node, ast.Attribute):
        raise ParseError("disallowed_node", "Attribute")
    if isinstance(node, ast.Lambda):
        raise ParseError("disallowed_node", "Lambda")

    # Recurse over children
    for child in ast.iter_child_nodes(node):
        # Names must match identifier regex
        if isinstance(child, ast.Name):
            if not ALLOWED_NAME_RE.match(child.id):
                raise ParseError("disallowed_name", child.id)
        _count_and_check_ast(child, depth + 1, counter)

    return counter["count"]

def _ast_to_sympy(node: ast.AST) -> sp.Expr:
    """Convert a vetted AST node (from ast.parse(..., mode='eval')) to a sympy expression."""
    if isinstance(node, ast.Expression):
        return _ast_to_sympy(node.body)
    if isinstance(node, ast.BinOp):
        left = _ast_to_sympy(node.left)
        right = _ast_to_sympy(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.Pow):
            return sp.Pow(left, right)
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.FloorDiv):
            return left // right
        # unsupported op
        raise ParseError("disallowed_operator", type(op).__name__)
    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_sympy(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise ParseError("disallowed_operator", type(node.op).__name__)
    if isinstance(node, ast.Constant):
        # ast.Constant covers numbers and strings in py3.8+
        val = node.value
        if isinstance(val, (int, float)):
            return sp.Integer(val) if isinstance(val, int) else sp.Float(val)
        raise ParseError("disallowed_constant", str(type(val).__name__))
    if isinstance(node, ast.Num):  # older ast.Num
        return sp.Integer(node.n) if isinstance(node.n, int) else sp.Float(node.n)
    if isinstance(node, ast.Name):
        # treat as symbol
        name = node.id
        return sp.Symbol(name)
    if isinstance(node, ast.Tuple):
        # convert each element to tuple of sympy exprs (rare for simple formulas)
        return sp.Tuple(*[_ast_to_sympy(elt) for elt in node.elts])
    if isinstance(node, ast.List):
        return sp.Tuple(*[_ast_to_sympy(elt) for elt in node.elts])
    # fallback: unsupported
    raise ParseError("unsupported_node", type(node).__name__)

def parse_to_sympy(expr_str: str) -> sp.Expr:
    """Parse expr_str with AST whitelist and convert to sympy.Expr; raise ParseError on problems."""
    if not isinstance(expr_str, str):
        raise ParseError("invalid_type", None)
    s = expr_str.strip()
    if not s:
        raise ParseError("empty", None)
    if len(s) > MAX_EXPR_LENGTH:
        raise ParseError("too_long", str(len(s)))
    _check_disallowed_substrings(s)

    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError as e:
        raise ParseError("syntax_error", str(e))

    # Count nodes and check structure
    _count_and_check_ast(tree, depth=0, counter=None)

    # convert to sympy
    expr = _ast_to_sympy(tree)
    return expr

def try_parse(expr_str: str) -> Tuple[bool, str]:
    """Public wrapper: returns (success, info). On success info=str(sympy_expr). On failure info=short code."""
    try:
        expr = parse_to_sympy(expr_str)
        # return string form
        return True, str(expr)
    except ParseError as pe:
        # return short code
        return False, pe.code if pe.code else "parse_error"
    except Exception:
        return False, "parse_error"
