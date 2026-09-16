"""评估脚本：对模型生成结果做语法解析与量纲校验

输出：JSONL，每条包含 input, target, pred, parse_ok (bool), dim_ok (bool), notes
"""
import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ensure repo import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.services.dimension_validator import DimensionValidator
import sympy as sp


def try_parse(expr_str):
    try:
        # naive parse: sympy can parse many python-like expressions
        expr = sp.sympify(expr_str)
        return True, str(expr)
    except Exception as e:
        return False, str(e)


def evaluate_model(model_dir: str, eval_file: str, output: str, max_length: int = 128, batch_size: int = 16, device: str = None):
    """
    Batched evaluation that writes JSONL to output.
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
        batch_raw_items = []

        def flush_batch():
            if not batch_srcs:
                return
            inputs = tokenizer(batch_srcs, return_tensors='pt', padding=True, truncation=True).to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=max_length, num_beams=4)
            preds = tokenizer.batch_decode(outputs, skip_special_tokens=True)
            for src, tgt, pred in zip(batch_srcs, batch_tgts, preds):
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
            # clear batch containers
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
    args = parser.parse_args()

    evaluate_model(args.model_dir, args.eval_file, args.output, max_length=args.max_length, batch_size=args.batch_size, device=args.device)


if __name__ == '__main__':
    main()
