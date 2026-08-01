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


def try_parse(expr_str):
    try:
        # naive parse: replace power ** for sympy
        # sympy can parse many python-like expressions
        expr = sp.sympify(expr_str)
        return True, str(expr)
    except Exception as e:
        return False, str(e)


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
            input_text = "<FORMULA> " + src.strip() + " </FORMULA>"
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
