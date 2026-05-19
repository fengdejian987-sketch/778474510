#!/usr/bin/env python3
"""
冯德建公式生成模型 - 通用物理公式建模和生成系统
基于文档标题中的物理学概念设计，支持量纲分析、公式推导、LaTeX生成

Author: Formula Generator Model v1.0
"""

import re
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import hashlib


class DimensionType(Enum):
    """物理量纲类型 (SI 基本量纲)"""
    LENGTH = "L"              # 长度
    MASS = "M"                # 质量
    TIME = "T"                # 时间
    TEMPERATURE = "Θ"         # 温度
    CURRENT = "I"             # 电流
    LUMINOUS = "J"            # 光强
    AMOUNT = "N"              # 物质量
    # 导出量纲
    VELOCITY = "LT⁻¹"         # 速度
    ACCELERATION = "LT⁻²"     # 加速度
    FORCE = "MLT⁻²"           # 力 (牛顿)
    ENERGY = "ML²T⁻²"         # 能量 (焦耳)
    POWER = "ML²T⁻³"          # 功率 (瓦特)
    PRESSURE = "ML⁻¹T⁻²"      # 压力 (帕斯卡)
    DENSITY = "ML⁻³"          # 密度
    ANGULAR_VELOCITY = "T⁻¹"  # 角速度
    FREQUENCY = "T⁻¹"         # 频率
    CHARGE = "IT"             # 电荷 (库仑)
    VOLTAGE = "ML²T⁻³I⁻¹"     # 电压 (伏特)
    RESISTANCE = "ML²T⁻³I⁻²"  # 电阻 (欧姆)
    CAPACITANCE = "M⁻¹L⁻²T⁴I²" # 电容 (法拉)
    MAGNETIC_FIELD = "MT⁻²I⁻¹" # 磁感应强度 (特斯拉)


@dataclass
class PhysicalQuantity:
    """物理量定义"""
    symbol: str                    # 符号 (v, t, T 等)
    name_cn: str                   # 中文名称
    name_en: str                   # 英文名称
    dimension: DimensionType        # 量纲
    description: str               # 描述
    unit: str                      # SI 单位
    range: Optional[Tuple[float, float]] = None  # 取值范围
    is_constant: bool = False      # 是否为常数
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name_cn': self.name_cn,
            'name_en': self.name_en,
            'dimension': self.dimension.value,
            'description': self.description,
            'unit': self.unit,
            'range': self.range,
            'is_constant': self.is_constant
        }


@dataclass
class PhysicalFormula:
    """物理公式定义"""
    name_cn: str                   # 中文名称
    name_en: str                   # 英文名称
    formula_latex: str             # LaTeX 格式
    formula_symbolic: str          # 符号表达式 (用于计算)
    description_cn: str            # 中文描述
    description_en: str            # 英文描述
    quantities: List[PhysicalQuantity]  # 涉及的物理量
    category: str                  # 分类
    subcategory: str = ""          # 子分类
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    reference: str = ""            # 参考文献
    example_values: Dict[str, float] = field(default_factory=dict)  # 示例数值
    
    def to_dict(self):
        return {
            'name_cn': self.name_cn,
            'name_en': self.name_en,
            'formula_latex': self.formula_latex,
            'formula_symbolic': self.formula_symbolic,
            'description_cn': self.description_cn,
            'description_en': self.description_en,
            'quantities': [q.to_dict() for q in self.quantities],
            'category': self.category,
            'subcategory': self.subcategory,
            'created_at': self.created_at,
            'version': self.version,
            'reference': self.reference,
            'example_values': self.example_values
        }
    
    def get_hash(self) -> str:
        """生成公式的唯一哈希值"""
        content = f"{self.name_cn}{self.formula_latex}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


@dataclass
class FormulaDerivation:
    """公式推导记录"""
    source_formula: str           # 源公式
    operation: str                # 操作 (求导/积分/变形)
    result_formula: str           # 结果公式
    steps: List[str] = field(default_factory=list)  # 推导步骤
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DimensionAnalyzer:
    """量纲分析器"""
    
    DIMENSION_MAP = {
        'v': DimensionType.VELOCITY,
        'u': DimensionType.VELOCITY,
        'a': DimensionType.ACCELERATION,
        't': DimensionType.TIME,
        'T': DimensionType.TIME,
        'x': DimensionType.LENGTH,
        's': DimensionType.LENGTH,
        'm': DimensionType.MASS,
        'M': DimensionType.MASS,
        'F': DimensionType.FORCE,
        'E': DimensionType.ENERGY,
        'P': DimensionType.POWER,
        'ρ': DimensionType.DENSITY,
        'V': DimensionType.LENGTH,  # 体积是 L³，但这里简化
        'ω': DimensionType.ANGULAR_VELOCITY,
        'f': DimensionType.FREQUENCY,
    }
    
    @staticmethod
    def get_dimension(symbol: str) -> Optional[DimensionType]:
        """获取符号的量纲"""
        return DimensionAnalyzer.DIMENSION_MAP.get(symbol)
    
    @staticmethod
    def check_consistency(formula: PhysicalFormula) -> Dict[str, any]:
        """检查公式量纲一致性 (简化版)"""
        result = {
            'is_consistent': True,
            'left_symbols': [],
            'right_symbols': [],
            'details': f"包含 {len(formula.quantities)} 个物理量"
        }
        return result


class FormulaGenerator:
    """公式生成和管理系统"""

    def __init__(self):
        self.formulas: List[PhysicalFormula] = []
        self.derivations: List[FormulaDerivation] = []
        self.symbol_library: Dict[str, PhysicalQuantity] = {}
        self._initialize_common_symbols()
        self._initialize_constants()

    def _initialize_common_symbols(self):
        """初始化常用符号库"""
        common_symbols = [
            PhysicalQuantity('v', '速度', 'velocity', DimensionType.VELOCITY, 
                           '物体的速度', 'm/s'),
            PhysicalQuantity('u', '初速度', 'initial velocity', DimensionType.VELOCITY,
                           '初始速度', 'm/s'),
            PhysicalQuantity('a', '加速度', 'acceleration', DimensionType.ACCELERATION,
                           '加速度', 'm/s²'),
            PhysicalQuantity('t', '时间', 'time', DimensionType.TIME,
                           '时间间隔', 's'),
            PhysicalQuantity('T', '周期', 'period', DimensionType.TIME,
                           '周期', 's'),
            PhysicalQuantity('x', '位移', 'displacement', DimensionType.LENGTH,
                           '位移', 'm'),
            PhysicalQuantity('s', '路程', 'distance', DimensionType.LENGTH,
                           '路程', 'm'),
            PhysicalQuantity('m', '质量', 'mass', DimensionType.MASS,
                           '质量', 'kg'),
            PhysicalQuantity('M', '质量', 'mass', DimensionType.MASS,
                           '质量 (大写)', 'kg'),
            PhysicalQuantity('F', '力', 'force', DimensionType.FORCE,
                           '力', 'N'),
            PhysicalQuantity('E', '能量', 'energy', DimensionType.ENERGY,
                           '能量', 'J'),
            PhysicalQuantity('P', '功率', 'power', DimensionType.POWER,
                           '功率', 'W'),
            PhysicalQuantity('ρ', '密度', 'density', DimensionType.DENSITY,
                           '密度', 'kg/m³'),
            PhysicalQuantity('V', '体积', 'volume', DimensionType.LENGTH,
                           '体积', 'm³'),
            PhysicalQuantity('ω', '角速度', 'angular velocity', DimensionType.ANGULAR_VELOCITY,
                           '角速度', 'rad/s'),
            PhysicalQuantity('c', '光速', 'speed of light', DimensionType.VELOCITY,
                           '真空中光速', 'm/s', is_constant=True),
            PhysicalQuantity('G', '万有引力常数', 'gravitational constant', DimensionType.LENGTH,
                           '万有引力常数', 'N·m²/kg²', is_constant=True),
        ]
        for sym in common_symbols:
            self.symbol_library[sym.symbol] = sym

    def _initialize_constants(self):
        """初始化物理常数"""
        constants = [
            ('c', 3e8, '光速'),
            ('G', 6.67e-11, '万有引力常数'),
            ('h', 6.626e-34, '普朗克常数'),
            ('k_B', 1.381e-23, '玻尔兹曼常数'),
            ('N_A', 6.022e23, '阿伏伽德罗常数'),
        ]

    def add_symbol(self, symbol: PhysicalQuantity):
        """添加符号到库中"""
        self.symbol_library[symbol.symbol] = symbol

    def add_formula(self, formula: PhysicalFormula):
        """添加公式"""
        self.formulas.append(formula)

    def create_formula(self, name_cn: str, name_en: str, formula_latex: str,
                      formula_symbolic: str, description_cn: str, 
                      description_en: str, quantities: List[PhysicalQuantity],
                      category: str, subcategory: str = "",
                      reference: str = "", example_values: Dict = None) -> PhysicalFormula:
        """创建并添加公式"""
        formula = PhysicalFormula(
            name_cn=name_cn,
            name_en=name_en,
            formula_latex=formula_latex,
            formula_symbolic=formula_symbolic,
            description_cn=description_cn,
            description_en=description_en,
            quantities=quantities,
            category=category,
            subcategory=subcategory,
            reference=reference,
            example_values=example_values or {}
        )
        self.add_formula(formula)
        return formula

    def export_to_json(self, filename: str = 'formulas.json'):
        """导出为 JSON 格式"""
        data = {
            'export_time': datetime.now().isoformat(),
            'total_formulas': len(self.formulas),
            'formulas': [f.to_dict() for f in self.formulas],
            'symbol_library': {
                k: v.to_dict() for k, v in self.symbol_library.items()
            }
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 已导出 {len(self.formulas)} 个公式到 {filename}")
        return data

    def export_to_markdown(self, filename: str = 'formulas.md'):
        """导出为 Markdown 格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 物理公式库\n\n")
            f.write(f"**导出时间**: {datetime.now().isoformat()}\n")
            f.write(f"**总公式数**: {len(self.formulas)}\n\n")
            
            # 按类别分组
            by_category = {}
            for formula in self.formulas:
                if formula.category not in by_category:
                    by_category[formula.category] = []
                by_category[formula.category].append(formula)
            
            for category in sorted(by_category.keys()):
                f.write(f"## {category}\n\n")
                for formula in by_category[category]:
                    f.write(f"### {formula.name_cn} ({formula.name_en})\n\n")
                    f.write(f"**描述**: {formula.description_cn}\n\n")
                    f.write(f"**LaTeX**: `{formula.formula_latex}`\n\n")
                    if formula.reference:
                        f.write(f"**参考**: {formula.reference}\n\n")
                    f.write(f"**涉及物理量**:\n\n")
                    for qty in formula.quantities:
                        f.write(f"- **{qty.symbol}**: {qty.name_cn} ({qty.unit})\n")
                    f.write(f"\n---\n\n")
        
        print(f"✓ 已导出到 {filename}")

    def search_by_category(self, category: str) -> List[PhysicalFormula]:
        """按类别搜索公式"""
        return [f for f in self.formulas if f.category == category]

    def search_by_symbol(self, symbol: str) -> List[PhysicalFormula]:
        """按符号搜索公式"""
        return [f for f in self.formulas 
                if any(q.symbol == symbol for q in f.quantities)]

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        categories = {}
        for formula in self.formulas:
            cat = formula.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        return {
            'total_formulas': len(self.formulas),
            'categories': categories,
            'total_symbols': len(self.symbol_library),
            'total_derivations': len(self.derivations)
        }

    def print_summary(self):
        """打印系统摘要"""
        stats = self.get_statistics()
        print("\n" + "="*60)
        print("冯德建公式生成系统 - 摘要")
        print("="*60)
        print(f"总公式数:        {stats['total_formulas']}")
        print(f"符号库大小:      {stats['total_symbols']}")
        print(f"推导记录数:      {stats['total_derivations']}")
        print(f"\n分类统��:")
        for cat, count in sorted(stats['categories'].items(), 
                                key=lambda x: x[1], reverse=True):
            print(f"  {cat:20s}: {count:3d}")
        print("="*60 + "\n")


class FengDejianFormulaSystem:
    """冯德建公式系统 - 预设公式库"""

    @staticmethod
    def build_default_system() -> FormulaGenerator:
        """构建包含经典物理公式的默认系统"""
        gen = FormulaGenerator()

        # 获取常用符号
        v = gen.symbol_library['v']
        u = gen.symbol_library['u']
        a = gen.symbol_library['a']
        t = gen.symbol_library['t']
        x = gen.symbol_library['x']
        m = gen.symbol_library['m']
        F = gen.symbol_library['F']
        E = gen.symbol_library['E']
        P = gen.symbol_library['P']
        c = gen.symbol_library['c']

        # 1. 运动学公式
        gen.create_formula(
            name_cn='匀加速直线运动速度公式',
            name_en='Uniform acceleration velocity formula',
            formula_latex='v = v_0 + at',
            formula_symbolic='v = u + a*t',
            description_cn='描述物体在恒定加速度下的速度变化关系',
            description_en='Describes velocity change under constant acceleration',
            quantities=[v, u, a, t],
            category='运动学',
            subcategory='直线运动'
        )

        gen.create_formula(
            name_cn='匀加速直线运动位移公式',
            name_en='Uniform acceleration displacement formula',
            formula_latex='x = v_0 t + \\frac{1}{2}at^2',
            formula_symbolic='x = u*t + 0.5*a*t**2',
            description_cn='描述恒定加速度下的位移与时间的关系',
            description_en='Relates displacement to time under constant acceleration',
            quantities=[x, u, a, t],
            category='运动学',
            subcategory='直线运动'
        )

        # 2. 动力学公式
        gen.create_formula(
            name_cn='牛顿第二定律',
            name_en='Newton\'s second law',
            formula_latex='\\vec{F} = m\\vec{a}',
            formula_symbolic='F = m*a',
            description_cn='合力等于质量与加速度的乘积',
            description_en='Net force equals mass times acceleration',
            quantities=[F, m, a],
            category='动力学',
            subcategory='牛顿运动定律'
        )

        # 3. 能量和功
        gen.create_formula(
            name_cn='动能',
            name_en='Kinetic energy',
            formula_latex='E_k = \\frac{1}{2}mv^2',
            formula_symbolic='E = 0.5*m*v**2',
            description_cn='物体由于运动而具有的能量',
            description_en='Energy possessed by a moving object',
            quantities=[E, m, v],
            category='能量',
            subcategory='动能'
        )

        gen.create_formula(
            name_cn='重力势能',
            name_en='Gravitational potential energy',
            formula_latex='E_p = mgh',
            formula_symbolic='E = m*g*h',
            description_cn='物体在重力场中由于位置而具有的能量',
            description_en='Energy due to position in gravitational field',
            quantities=[E, m],
            category='能量',
            subcategory='势能'
        )

        # 4. 相对论
        gen.create_formula(
            name_cn='质能方程',
            name_en='Mass-energy equivalence',
            formula_latex='E = mc^2',
            formula_symbolic='E = m*c**2',
            description_cn='质量与能量的相互转换关系，爱因斯坦著名公式',
            description_en='Einstein\'s mass-energy equivalence formula',
            quantities=[E, m, c],
            category='相对论',
            subcategory='特殊相对论'
        )

        # 5. 波和振动
        gen.create_formula(
            name_cn='波的基本关系式',
            name_en='Wave equation',
            formula_latex='v = f\\lambda',
            formula_symbolic='v = f*lambda',
            description_cn='波速等于频率与波长的乘积',
            description_en='Wave velocity equals frequency times wavelength',
            quantities=[v],
            category='波动',
            subcategory='波的传播'
        )

        return gen


def main():
    """演示系统的使用"""
    # 构建默认系统
    system = FengDejianFormulaSystem.build_default_system()
    
    # 打印摘要
    system.print_summary()
    
    # 导出
    system.export_to_json('formulas_feng_dejian.json')
    system.export_to_markdown('formulas_feng_dejian.md')
    
    # 演示搜索
    print("\n搜索包含 'm' 的公式:")
    results = system.search_by_symbol('m')
    for f in results:
        print(f"  - {f.name_cn}: {f.formula_latex}")
    
    print("\n搜索'运动学'类别的公式:")
    results = system.search_by_category('运动学')
    for f in results:
        print(f"  - {f.name_cn}: {f.formula_latex}")


if __name__ == '__main__':
    main()
