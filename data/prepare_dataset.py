"""生成合成训练数据的简单脚本，用模板生成 description -> canonical_formula 对

输出 JSONL 文件，每行一个 JSON: {"description":..., "canonical_formula":...}

注：仅用于 POC 数据生成，请结合真实标注数据扩展。
"""

import json
import random
from pathlib import Path

TEMPLATES = [
    ("动能公式，质量 m，速度 v", "E = 1/2 * m * v ** 2"),
    ("质能方程", "E = m * c ** 2"),
    ("牛顿第二定律，力 F，质量 m，得到加速度 a", "F = m * a"),
    ("动量公式，质量 m，速度 v", "p = m * v"),
    ("功率公式，力 F，速度 v", "P = F * v"),
]

VAR_TEMPLATES = [
    ("{formula}，用变量 {m} 表示质量，用 {v} 表示速度", "{canonical}"),
]

def synthesize(n, out_path="data/train.jsonl"):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for i in range(n):
            t = random.choice(TEMPLATES)
            desc, can = t
            # occasionally substitute variable names
            if random.random() < 0.3:
                mvar = random.choice(['m', 'm1', 'mass'])
                vvar = random.choice(['v', 'u', 'vel'])
                can_sub = can.replace('m', mvar).replace('v', vvar)
                desc_sub = desc + f"（变量: {mvar}, {vvar}）"
                item = {"description": desc_sub, "formula": can_sub}
            else:
                item = {"description": desc, "formula": can}
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    synthesize(2000, out_path="data/train.jsonl")
