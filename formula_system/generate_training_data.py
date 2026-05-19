#!/usr/bin/env python3
"""
生成训练数据脚本 - 从README自动转换为 input->LaTeX 训练对

使用方法:
python generate_training_data.py --readme_path ../README.md --output data_train.jsonl

生成的JSONL格式:
{"input":"用一句话描述：牛顿第二定律","target":"F = m \\cdot a"}
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import random
from collections import defaultdict

# 物理公式映射库（从README标题自动映射）
PHYSICS_FORMULA_DATABASE = {
    # 基础力学
    "牛顿第二定律": {
        "formulas": [
            "F = m \\cdot a",
            "\\vec{F} = m\\vec{a}"
        ],
        "category": "运动学",
        "keywords": ["牛顿", "第二定律", "力", "加速度"]
    },
    "万有引力定律": {
        "formulas": [
            "F = G \\frac{m_1 m_2}{r^2}",
            "F_g = \\frac{GM m}{r^2}"
        ],
        "category": "万有引力",
        "keywords": ["万有引力", "重力", "引力"]
    },
    "动能定理": {
        "formulas": [
            "W = \\Delta E_k = \\frac{1}{2}m v^2 - \\frac{1}{2}m v_0^2",
            "E_k = \\frac{1}{2}m v^2"
        ],
        "category": "能量",
        "keywords": ["动能", "速度", "动能定理"]
    },
    
    # 相对论
    "质能方程": {
        "formulas": [
            "E = mc^2",
            "E_0 = mc^2"
        ],
        "category": "相对论",
        "keywords": ["能量", "质量", "光速", "质能"]
    },
    
    # 宇宙物理（冯德建）
    "宇宙物质能量守恒": {
        "formulas": [
            "\\frac{dE}{dt} = 0",
            "E_{total} = E_{matter} + E_{radiation} = const"
        ],
        "category": "宇宙学",
        "keywords": ["能量守恒", "物质", "宇宙", "守恒"]
    },
    "空间密度与轴向力": {
        "formulas": [
            "\\rho = \\frac{m}{V}",
            "F_{axial} = \\rho \\cdot A \\cdot v^2"
        ],
        "category": "流体力学",
        "keywords": ["密度", "轴向力", "空间"]
    },
    
    # 电磁学
    "库仑定律": {
        "formulas": [
            "F = k\\frac{q_1 q_2}{r^2}",
            "F_e = \\frac{1}{4\\pi\\epsilon_0}\\frac{q_1 q_2}{r^2}"
        ],
        "category": "电磁学",
        "keywords": ["库仑", "电力", "电荷"]
    },
    "欧姆定律": {
        "formulas": [
            "U = IR",
            "I = \\frac{U}{R}"
        ],
        "category": "电磁学",
        "keywords": ["欧姆", "电阻", "电压", "电流"]
    },
    "焦耳热": {
        "formulas": [
            "Q = I^2 R t",
            "Q = \\frac{U^2}{R}t"
        ],
        "category": "电磁学",
        "keywords": ["焦耳热", "热能", "电阻"]
    },
    
    # 热力学
    "理想气体状态方程": {
        "formulas": [
            "PV = nRT",
            "PV = Nk_B T"
        ],
        "category": "热力学",
        "keywords": ["气体", "理想", "状态方程", "压力"]
    },
    
    # 波动光学
    "波的速度公式": {
        "formulas": [
            "v = f\\lambda",
            "v = \\frac{\\lambda}{T}"
        ],
        "category": "波动",
        "keywords": ["波速", "频率", "波长"]
    },
    "多普勒效应": {
        "formulas": [
            "f' = f\\frac{v + v_o}{v - v_s}",
            "\\Delta f = f\\frac{v_{rel}}{v}"
        ],
        "category": "波动",
        "keywords": ["多普勒", "频率", "相对速度"]
    },
    "折射定律": {
        "formulas": [
            "n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2",
            "\\sin\\theta_c = \\frac{n_2}{n_1}"
        ],
        "category": "光学",
        "keywords": ["折射", "光线", "折射率"]
    },
    
    # 微观物理
    "微观宏观物理": {
        "formulas": [
            "E = hf",
            "E = \\hbar\\omega"
        ],
        "category": "量子物理",
        "keywords": ["能量", "频率", "光子", "普朗克"]
    },
    
    # 统一物理场
    "统一物理场量": {
        "formulas": [
            "\\Phi = \\frac{F}{q}",
            "\\Phi = \\frac{E}{\\epsilon_0}"
        ],
        "category": "电磁学",
        "keywords": ["场", "物理", "统一", "场量"]
    },
}

# 自然语言模板（用于数据增强）
DESCRIPTION_TEMPLATES = {
    "定义": [
        "给出定义：{}",
        "什么是{}？写出其公式",
        "描述{}的数学表达式",
        "{}的定义公式是什么？"
    ],
    "推导": [
        "推导{}的公式",
        "从基本原理推导{}",
        "{}的推导过程",
        "用符号表示{}"
    ],
    "应用": [
        "应用{}计算",
        "{}在实际中的应用公式",
        "{}的应用形式",
        "{}的具体表达"
    ],
    "英文": [
        "Write the formula for {}",
        "Express {} in mathematical form",
        "The formula of {} is",
        "Describe {} using equations"
    ]
}


@dataclass
class TrainingExample:
    """训练样本"""
    input: str
    target: str
    category: str
    source: str  # 来源（哪个公式）
    language: str  # 语言（Chinese/English）


class DataGenerator:
    """训练数据生成器"""
    
    def __init__(self):
        self.examples: List[TrainingExample] = []
        self.stats = defaultdict(int)
    
    def extract_title_from_readme(self, readme_path: str) -> List[str]:
        """从README提取文档标题"""
        titles = []
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取markdown链接标题 [标题](url)
        pattern = r'\[([^\]]+)\]\('
        matches = re.findall(pattern, content)
        
        for match in matches:
            # 清理标题
            clean_title = re.sub(r'(上传|正在上传|Uploading).*', '', match).strip()
            # 移除重复中文
            clean_title = re.sub(r'(.+?)(\1)+', r'\1', clean_title)
            if clean_title and len(clean_title) > 3:
                titles.append(clean_title)
        
        return list(set(titles))  # 去重
    
    def match_formula(self, title: str) -> Tuple[List[str], str, str]:
        """从标题匹配公式"""
        # 直接匹配
        if title in PHYSICS_FORMULA_DATABASE:
            formula_data = PHYSICS_FORMULA_DATABASE[title]
            return formula_data["formulas"], formula_data["category"], title
        
        # 关键词匹配
        title_lower = title.lower()
        for formula_name, formula_data in PHYSICS_FORMULA_DATABASE.items():
            keywords = formula_data["keywords"]
            if any(kw in title_lower for kw in keywords):
                return formula_data["formulas"], formula_data["category"], formula_name
        
        # 默认返回空
        return [], "未分类", title
    
    def generate_examples_from_readme(self, readme_path: str) -> List[TrainingExample]:
        """从README生成训练样本"""
        titles = self.extract_title_from_readme(readme_path)
        
        print(f"提取到 {len(titles)} 个唯一标题")
        
        for title in titles:
            formulas, category, matched_name = self.match_formula(title)
            
            if not formulas:
                self.stats["未匹配"] += 1
                # 创建通用样本
                example = TrainingExample(
                    input=f"给出定义：{title}",
                    target=f"未知公式",
                    category="未分类",
                    source=title,
                    language="Chinese"
                )
                self.examples.append(example)
                continue
            
            # 为每个公式创建多个样本（数据增强）
            for i, formula in enumerate(formulas):
                # 中文版本
                templates = DESCRIPTION_TEMPLATES["定义"]
                for template in templates[:2]:
                    example = TrainingExample(
                        input=template.format(title),
                        target=formula,
                        category=category,
                        source=matched_name,
                        language="Chinese"
                    )
                    self.examples.append(example)
                
                # 英文版本
                en_title = self._translate_to_english(title)
                en_templates = DESCRIPTION_TEMPLATES["英文"]
                for template in en_templates[:2]:
                    example = TrainingExample(
                        input=template.format(en_title),
                        target=formula,
                        category=category,
                        source=matched_name,
                        language="English"
                    )
                    self.examples.append(example)
            
            self.stats["已匹配"] += 1
    
    def _translate_to_english(self, chinese_title: str) -> str:
        """简单的中英文翻译映射"""
        translation_map = {
            "牛顿第二定律": "Newton's Second Law",
            "万有引力定律": "Universal Gravitation",
            "动能定理": "Kinetic Energy Theorem",
            "质能方程": "Mass-Energy Equation",
            "宇宙物质能量守恒": "Universal Matter Energy Conservation",
            "库仑定律": "Coulomb's Law",
            "欧姆定律": "Ohm's Law",
        }
        return translation_map.get(chinese_title, chinese_title)
    
    def to_jsonl(self, output_file: str):
        """导出为JSONL格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in self.examples:
                json_line = {
                    "input": example.input,
                    "target": example.target,
                    "category": example.category,
                    "source": example.source,
                    "language": example.language
                }
                f.write(json.dumps(json_line, ensure_ascii=False) + '\n')
        
        print(f"✓ 已生成 {len(self.examples)} 个训练样本到 {output_file}")
    
    def split_train_valid(self, output_file: str, train_file: str, valid_file: str, ratio: float = 0.8):
        """分割训练集和验证集"""
        random.shuffle(self.examples)
        split_idx = int(len(self.examples) * ratio)
        
        train_examples = self.examples[:split_idx]
        valid_examples = self.examples[split_idx:]
        
        # 保存训练集
        with open(train_file, 'w', encoding='utf-8') as f:
            for ex in train_examples:
                f.write(json.dumps({
                    "input": ex.input,
                    "target": ex.target,
                    "category": ex.category
                }, ensure_ascii=False) + '\n')
        
        # 保存验证集
        with open(valid_file, 'w', encoding='utf-8') as f:
            for ex in valid_examples:
                f.write(json.dumps({
                    "input": ex.input,
                    "target": ex.target,
                    "category": ex.category
                }, ensure_ascii=False) + '\n')
        
        print(f"✓ 训练集: {len(train_examples)} 样本 -> {train_file}")
        print(f"✓ 验证集: {len(valid_examples)} 样本 -> {valid_file}")
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("训练数据生成统计")
        print("="*60)
        print(f"总样本数:      {len(self.examples)}")
        print(f"已匹配公式:    {self.stats['已匹配']}")
        print(f"未匹配标题:    {self.stats['未匹配']}")
        
        # 按类别统计
        category_count = defaultdict(int)
        for example in self.examples:
            category_count[example.category] += 1
        
        print("\n按类别统计:")
        for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
        
        # 按语言统计
        lang_count = defaultdict(int)
        for example in self.examples:
            lang_count[example.language] += 1
        
        print("\n按语言统计:")
        for lang, count in sorted(lang_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {lang}: {count}")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="从README生成训练数据")
    parser.add_argument("--readme_path", type=str, default="README.md", help="README文件路径")
    parser.add_argument("--output", type=str, default="data_train.jsonl", help="输出文件")
    parser.add_argument("--split", action="store_true", help="是否分割训练/验证集")
    
    args = parser.parse_args()
    
    generator = DataGenerator()
    
    # 从README生成样本
    generator.generate_examples_from_readme(args.readme_path)
    
    # 打印统计
    generator.print_stats()
    
    if args.split:
        # 分割为训练/验证集
        train_file = args.output.replace(".jsonl", "_train.jsonl")
        valid_file = args.output.replace(".jsonl", "_valid.jsonl")
        generator.split_train_valid(args.output, train_file, valid_file)
    else:
        # 直接导出
        generator.to_jsonl(args.output)


if __name__ == "__main__":
    main()
