"""评估脚本：对模型生成结果做语法解析与量纲校验

输出：JSONL，每条包含 input, target, pred, parse_ok (bool), dim_ok (bool), notes
"""
import argparse
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ensure repo import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.services.dimension_validator import DimensionValidator
import sympy as sp
import multiprocessing
import time
import os


# Security: safe parsing with sandboxing and resource limits
MAX_EXPR_LENGTH = 2000  # reject extremely long expressions early
PARSE_TIMEOUT = 3  # seconds CPU time limit for parsing
PARSE_MEM_MB = 200  # memory limit for parser process
DISALLOWED_SUBSTRINGS = ["__", "import", "os.", "sys.", "eval(", "exec(", "subprocess", "open(", "lambda ", "getattr("]


def _worker_parse(expr_str, out_queue, timeout, mem_mb):
    """Worker process: set resource limits and parse expression using sympy."""
    try:
        # Restrict resources where supported (POSIX)
        try:
            import resource

            # address space (virtual memory)
            mem_bytes = int(mem_mb) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            # CPU time (seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
            # smaller file descriptors
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
            except Exception:
                pass
        except Exception:
            # resource may not exist on some platforms (Windows) — best effort
            pass

        # Minimal namespace for parsing
        local_dict = {}
        global_dict = {}

        # Use sympy's safe parsing functions
        from sympy.parsing.sympy_parser import parse_expr
        # Limit allowed transformations to avoid evaluation of functions
        transformations = (sp.parsing.sympy_parser.standard_transformations,)

        # Actually parse
        expr = parse_expr(expr_str, local_dict=local_dict, global_dict=global_dict, transformations=transformations)
        out_queue.put((True, str(expr)))
    except Exception as e:
        # Do not send full traceback to parent; just a short repr
        out_queue.put((False, repr(e)))


def try_parse(expr_str: str):
    """Attempt to parse expr_str in a sandboxed subprocess with limits.

    Returns (bool success, str info).
    Success True -> info is parsed expression string.
    Success False -> info is a short failure code/message (no sensitive traceback).
    """
    if not isinstance(expr_str, str):
        return False, "invalid_type"
    s = expr_str.strip()
    if len(s) == 0:
        return False, "empty"
    # quick reject on disallowed patterns or excessive length
    lower = s.lower()
    for bad in DISALLOWED_SUBSTRINGS:
        if bad in lower:
            return False, "disallowed_token"
    if len(s) > MAX_EXPR_LENGTH:
        return False, "too_long"

    # Use multiprocessing to isolate parse and enforce timeout/memory
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue(1)
    p = ctx.Process(target=_worker_parse, args=(s, q, PARSE_TIMEOUT, PARSE_MEM_MB))
    p.start()
    try:
        success, info = q.get(timeout=PARSE_TIMEOUT + 1)
    except Exception:
        # Timeout or queue failure: ensure process killed
        try:
            p.terminate()
        except Exception:
            pass
        p.join(timeout=1)
        return False, "parse_timeout"
    finally:
        if p.is_alive():
            try:
                p.terminate()
            except Exception:
                pass
            p.join(timeout=1)

    # sanitize info length
    if isinstance(info, str) and len(info) > 1000:
        info = info[:1000] + "..."

    return bool(success), info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--eval_file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max_length", type=int, default=128)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_dir)

    dv = DimensionValidator()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.eval_file, 'r', encoding='utf-8') as fin, open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            item = json.loads(line)
            src = item.get('description') or item.get('input')
            tgt = item.get('formula') or item.get('target') or item.get('canonical_formula')
            input_text = "<FORMULA> " + (src or "").strip() + " </FORMULA>"
            inputs = tokenizer(input_text, return_tensors='pt')
            outputs = model.generate(**inputs, max_length=args.max_length, num_beams=4)
            pred = tokenizer.decode(outputs[0], skip_special_tokens=True)

            parse_ok, parse_info = try_parse(pred)
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


if __name__ == '__main__':
    main()
