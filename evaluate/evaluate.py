"""评估脚本：对模型生成结果做语法解析与量纲校验

输出：JSONL，每条包含 input, target, pred, parse_ok (bool), dim_ok (bool), notes
"""
import argparse
import json
import sys
from pathlib import Path
import concurrent.futures
from functools import lru_cache
import re

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ensure repo import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.services.dimension_validator import DimensionValidator
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application


# allowed parsing transformations
_TRANSFORMS = (standard_transformations + (implicit_multiplication_application,))
_SYMBOL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _extract_symbols(expr_str):
    return sorted(set(_SYMBOL_RE.findall(expr_str)))


def _safe_parse_worker(expr_str: str) -> str:
    """Run inside a separate process: create sympy Symbols for tokens and parse safely.

    Returns canonical string repr of parsed expression.
    Raises exceptions on disallowed tokens or parse errors.
    """
    tokens = _extract_symbols(expr_str)
    local_dict = {}
    for t in tokens:
        if t.lower() in ("eval", "exec", "open", "os", "sys", "subprocess", "__import__"):
            raise ValueError(f"disallowed token: {t}")
        # create simple Symbol objects
        local_dict[t] = sp.Symbol(t)
    # use parse_expr with limited transformations and no builtin/functions
    expr = parse_expr(expr_str, local_dict=local_dict, transformations=_TRANSFORMS, evaluate=True)
    return str(expr)


def _parse_via_worker(expr_str: str, timeout: float = 2.0) -> str:
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as exe:
        future = exe.submit(_safe_parse_worker, expr_str)
        # will raise TimeoutError or other exceptions to caller
        return future.result(timeout=timeout)


# cache parses on (expr_str, timeout) to avoid re-parsing identical expressions
_cached_parse = lru_cache(maxsize=8192)(_parse_via_worker)


def safe_parse(expr_str: str, timeout: float = 2.0):
    """Safely parse expr_str in a worker process with timeout.

    Returns (True, normalized_expr_str) on success, else (False, error_message).
    """
    if not isinstance(expr_str, str) or len(expr_str.strip()) == 0:
        return False, "empty input"

    # short-circuit numeric literals
    s = expr_str.strip()
    if s.replace('.', '', 1).lstrip('+-').isdigit():
        return True, s

    try:
        parsed = _cached_parse(expr_str, timeout)
        return True, parsed
    except concurrent.futures.TimeoutError:
        return False, f"parse timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def evaluate_model(model_dir: str, eval_file: str, output: str, max_length: int = 128, batch_size: int = 16, device: str = None, parse_timeout: float = 2.0):
    """
    Batched evaluation that writes JSONL to output.
    parse_timeout controls per-expression parsing timeout in seconds.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
    model.to(device)
    model.eval()

    dv = DimensionValidator()

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(eval_file, 'r', encoding='utf-8') as fin, open(out_path, 'w', encoding='utf-8') as fout:
        batch_srcs = []
        batch_tgts = []

        def flush_batch():
            if not batch_srcs:
                return
            inputs = tokenizer(batch_srcs, return_tensors='pt', padding=True, truncation=True).to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=max_length, num_beams=4)
            preds = tokenizer.batch_decode(outputs, skip_special_tokens=True)

            # parse & validate each prediction (safe_parse with timeout)
            for src, tgt, pred in zip(batch_srcs, batch_tgts, preds):
                ok, info = safe_parse(pred, timeout=parse_timeout)
                parse_ok, parse_info = ok, info
                dim_res = dv.validate_formula(pred) if parse_ok else {'is_valid': False}
                res = {
                    'input': src,
                    'target': tgt,
                    'pred': pred,
                    'parse_ok': parse_ok,
                    'parse_info': parse_info,
                    'dim_ok': bool(dim_res.get('is_valid')),
                    'dim_details': dim_res,
                }
                fout.write(json.dumps(res, ensure_ascii=False) + '\n')
            batch_srcs.clear()
            batch_tgts.clear()

        for line in fin:
            item = json.loads(line)
            src = item.get('description') or item.get('input') or ""
            tgt = item.get('formula') or item.get('target') or item.get('canonical_formula') or ""
            input_text = "<FORMULA> " + src.strip() + " </FORMULA>"
            batch_srcs.append(input_text)
            batch_tgts.append(tgt)
            if len(batch_srcs) >= batch_size:
                flush_batch()

        # flush remaining
        flush_batch()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--eval_file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max_length", type=int, default=128)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--parse_timeout", type=float, default=2.0)
    args = parser.parse_args()

    evaluate_model(args.model_dir, args.eval_file, args.output, max_length=args.max_length, batch_size=args.batch_size, device=args.device, parse_timeout=args.parse_timeout)


if __name__ == '__main__':
    main()
