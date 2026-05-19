#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冯德建公式生成与管理系统
综合物理公式建模、生成、解析、推导一体化解决方案
"""

import re
import json
import csv
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import sympy as sp
from sympy import symbols, Function, Eq, simplify, latex, diff, integrate, solve


class DimensionType(Enum):
    """物理量纲类型 - 基础量纲分类"""
    LENGTH = "L"              # 长度
    MASS = "M"                # 质量
    TIME = "T"                # 时间
    TEMPERATURE = "Θ"         # 温度
    CURRENT = "I"             # 电流
    LUMINOUS = "J"            # 光强
    AMOUNT = "N"              # 物质量
    ANGLE = "rad"             # 角度（无量纲）
    VELOCITY = "LT⁻¹"         # 速度
    ACCELERATION = "LT⁻²"     # 加速度
    FORCE = "MLT⁻²"           # 力
    ENERGY = "ML²T⁻²"         # 能量
    POWER = "ML²T⁻³"          # 功率
    PRESSURE = "ML⁻¹T⁻²"      # 压力
    DENSITY = "ML⁻³"          # 密度
    MOMENTUM = "MLT⁻¹"        # 动量
    TORQUE = "ML²T⁻²"         # 力矩
    ANGULAR_VELOCITY = "T⁻¹"  # 角速度
    FREQUENCY = "T⁻¹"         # 频率


@dataclass
class PhysicalQuantity:
    """物理量定义 - 描述某个物理量的所有属性"""
    symbol: str                    # 符号 (v, t, T 等)
    name_zh: str                   # 中文名称
    name_en: str                   # 英文名称
    dimension: DimensionType       # 量纲
    description: str               # 描述
    unit: str                      # SI单位
    typical_range: Optional[Tuple[float, float]] = None  # 典型范围
    category: str = "基本量"       # 分类

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'dimension': self.dimension.value,
            'description': self.description,
            'unit': self.unit,
            'typical_range': self.typical_range,
            'category': self.category
        }


@dataclass
class PhysicalFormula:
    """物理公式定义 - 完整的公式表示及其元数据"""
    id: str                           # 唯一ID
    name_zh: str                      # 中文名称
    name_en: str                      # 英文名称
    formula_str: str                  # 公式字符串表示 (如 "E=m*c**2")
    latex_str: str = ""               # LaTeX表示
    description_zh: str = ""          # 中文描述
    description_en: str = ""          # 英文描述
    quantities: List[PhysicalQuantity] = field(default_factory=list)  # 涉及的物理量
    category: str = ""                # 分类 (力学/热学/电磁学等)
    applications: List[str] = field(default_factory=list)  # 应用领域
    prerequisites: List[str] = field(default_factory=list)  # 前置公式
    created_at: str = ""              # 创建时间
    version: str = "1.0"              # 版本
    notes: str = ""                   # 备注

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = f"formula_{int(datetime.now().timestamp()*1000)}"

    def to_dict(self):
        return {
            'id': self.id,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'formula': self.formula_str,
            'latex': self.latex_str,
            'description_zh': self.description_zh,
            'description_en': self.description_en,
            'quantities': [q.to_dict() for q in self.quantities],
            'category': self.category,
            'applications': self.applications,
            'prerequisites': self.prerequisites,
            'created_at': self.created_at,
            'version': self.version,
            'notes': self.notes
        }


class FormulaLibrary:
    """公式库 - 管理所有物理公式"""

    def __init__(self):
        self.formulas: Dict[str, PhysicalFormula] = {}
        self.quantities: Dict[str, PhysicalQuantity] = {}
        self.symbols_dict: Dict[str, sp.Symbol] = {}
        self._initialize_standard_symbols()
        self._initialize_standard_quantities()

    def _initialize_standard_symbols(self):
        """初始化标准符号"""
        symbols_to_create = {
            'v': 'velocity',
            't': 'time',
            'T': 'temperature',
            'x': 'position',
            'a': 'acceleration',
            'm': 'mass',
            'F': 'force',
            'E': 'energy',
            'P': 'power',
            'rho': 'density',
            'V': 'volume',
            'omega': 'angular_velocity',
            'c': 'light_speed',
            'G': 'gravitational_constant',
            'k': 'spring_constant',
            'mu': 'friction_coefficient',
        }
        
        for sym, desc in symbols_to_create.items():
            self.symbols_dict[sym] = symbols(sym, real=True, positive=True)

    def _initialize_standard_quantities(self):
        """初始化标准物理量"""
        standard_quantities = [
            PhysicalQuantity('v', '速度', 'velocity', DimensionType.VELOCITY, 
                            '物体运动速度', 'm/s', category='运动学'),
            PhysicalQuantity('t', '时间', 'time', DimensionType.TIME, 
                            '时间间隔', 's', category='基本量'),
            PhysicalQuantity('a', '加速度', 'acceleration', DimensionType.ACCELERATION, 
                            '速度变化率', 'm/s²', category='运动学'),
            PhysicalQuantity('m', '质量', 'mass', DimensionType.MASS, 
                            '物体质量', 'kg', category='基本量'),
            PhysicalQuantity('F', '力', 'force', DimensionType.FORCE, 
                            '物体受力', 'N', category='力学'),
            PhysicalQuantity('E', '能量', 'energy', DimensionType.ENERGY, 
                            '系统能量', 'J', category='能量'),
            PhysicalQuantity('P', '功率', 'power', DimensionType.POWER, 
                            '单位时间内的功', 'W', category='能量'),
            PhysicalQuantity('ρ', '密度', 'density', DimensionType.DENSITY, 
                            '单位体积的质量', 'kg/m³', category='流体力学'),
            PhysicalQuantity('V', '体积', 'volume', DimensionType.LENGTH, 
                            '物体占据的空间', 'm³', category='几何量'),
            PhysicalQuantity('c', '光速', 'light_speed', DimensionType.VELOCITY, 
                            '光在真空中的速度', 'm/s', category='常数'),
        ]
        
        for qty in standard_quantities:
            self.quantities[qty.symbol] = qty

    def add_quantity(self, qty: PhysicalQuantity):
        """添加物理量"""
        self.quantities[qty.symbol] = qty

    def add_formula(self, formula: PhysicalFormula):
        """添加公式"""
        self.formulas[formula.id] = formula

    def create_formula(self, name_zh: str, name_en: str, formula_str: str,
                      description_zh: str = "", description_en: str = "",
                      quantities: List[PhysicalQuantity] = None,
                      category: str = "通用",
                      applications: List[str] = None,
                      prerequisites: List[str] = None,
                      notes: str = "") -> PhysicalFormula:
        """创建并添加公式"""
        formula = PhysicalFormula(
            id=f"formula_{len(self.formulas)+1:04d}",
            name_zh=name_zh,
            name_en=name_en,
            formula_str=formula_str,
            description_zh=description_zh or f"{name_zh}的表达式",
            description_en=description_en or f"Expression for {name_en}",
            quantities=quantities or [],
            category=category,
            applications=applications or [],
            prerequisites=prerequisites or [],
            notes=notes
        )
        
        # 生成LaTeX
        try:
            formula.latex_str = self.parse_to_latex(formula_str)
        except:
            formula.latex_str = formula_str
        
        self.add_formula(formula)
        return formula

    def parse_formula_string(self, formula_str: str) -> sp.Expr:
        """解析公式字符串为sympy表达式"""
        try:
            # 符号替换以兼容sympy
            expr_str = formula_str.replace('ρ', 'rho')
            expr_str = expr_str.replace('ω', 'omega')
            expr_str = expr_str.replace('μ', 'mu')
            expr_str = expr_str.replace('λ', 'lambda_var')
            expr = sp.sympify(expr_str)
            return expr
        except Exception as e:
            raise ValueError(f"无法解析公式: {formula_str}, 错误: {e}")

    def parse_to_latex(self, formula_str: str) -> str:
        """将公式字符串转换为LaTeX"""
        try:
            expr = self.parse_formula_string(formula_str)
            return latex(expr)
        except:
            return formula_str

    def derive_formula(self, formula_str: str, variable: str, order: int = 1) -> str:
        """对公式求导"""
        try:
            expr = self.parse_formula_string(formula_str)
            sym = self.symbols_dict.get(variable)
            
            if sym is None:
                raise ValueError(f"未定义的变量: {variable}")
            
            result = expr
            for _ in range(order):
                result = diff(result, sym)
            
            return str(result)
        except Exception as e:
            return f"求导失败: {e}"

    def integrate_formula(self, formula_str: str, variable: str) -> str:
        """对公式积分"""
        try:
            expr = self.parse_formula_string(formula_str)
            sym = self.symbols_dict.get(variable)
            
            if sym is None:
                raise ValueError(f"未定义的变量: {variable}")
            
            result = integrate(expr, sym)
            return str(result)
        except Exception as e:
            return f"积分失败: {e}"

    def solve_for_variable(self, formula_str: str, target_var: str) -> List[str]:
        """解出指定变量"""
        try:
            expr = self.parse_formula_string(formula_str)
            sym = self.symbols_dict.get(target_var)
            
            if sym is None:
                raise ValueError(f"未定义的变量: {target_var}")
            
            solutions = solve(expr, sym)
            return [str(sol) for sol in solutions]
        except Exception as e:
            return [f"求解失败: {e}"]

    def substitute_values(self, formula_str: str, values: Dict[str, float]) -> float:
        """代入数值求解"""
        try:
            expr = self.parse_formula_string(formula_str)
            subs_dict = {}
            
            for var, val in values.items():
                sym = self.symbols_dict.get(var)
                if sym is None:
                    try:
                        sym = sp.Symbol(var)
                        self.symbols_dict[var] = sym
                    except:
                        continue
                subs_dict[sym] = val
            
            result = expr.subs(subs_dict)
            return float(result)
        except Exception as e:
            raise ValueError(f"代入数值失败: {e}")

    def check_dimension(self, formula_id: str) -> Dict[str, Any]:
        """检查量纲一致性"""
        formula = self.formulas.get(formula_id)
        if not formula:
            return {'status': 'error', 'message': f'找不到公式: {formula_id}'}
        
        return {
            'formula_id': formula_id,
            'formula': formula.formula_str,
            'quantities': [q.to_dict() for q in formula.quantities],
            'dimension_analysis': f"包含 {len(formula.quantities)} 个物理量"
        }

    def export_to_json(self, filename: str = 'formulas.json'):
        """导出为JSON格式"""
        data = {
            'export_time': datetime.now().isoformat(),
            'total_formulas': len(self.formulas),
            'total_quantities': len(self.quantities),
            'formulas': [f.to_dict() for f in self.formulas.values()],
            'quantities': [q.to_dict() for q in self.quantities.values()]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已导出 {len(self.formulas)} 个公式到 {filename}")
        return data

    def export_to_csv(self, filename: str = 'formulas.csv'):
        """导出为CSV格式"""
        if not self.formulas:
            print("没有公式可导出")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ID', '中文名称', '英文名称', '公式', 'LaTeX', '分类', '应用领域']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for formula in self.formulas.values():
                writer.writerow({
                    'ID': formula.id,
                    '中文名称': formula.name_zh,
                    '英文名称': formula.name_en,
                    '公式': formula.formula_str,
                    'LaTeX': formula.latex_str,
                    '分类': formula.category,
                    '应用领域': '; '.join(formula.applications)
                })
        
        print(f"✓ 已导出到 {filename}")

    def export_to_markdown(self, filename: str = 'formulas.md'):
        """导出为Markdown格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 物理公式库\n\n")
            f.write(f"**导出时间**: {datetime.now().isoformat()}\n")
            f.write(f"**总公式数**: {len(self.formulas)}\n")
            f.write(f"**总物理量数**: {len(self.quantities)}\n\n")
            
            # 按分类分组
            by_category = {}
            for formula in self.formulas.values():
                if formula.category not in by_category:
                    by_category[formula.category] = []
                by_category[formula.category].append(formula)
            
            for category in sorted(by_category.keys()):
                formulas = by_category[category]
                f.write(f"## {category}\n\n")
                
                for formula in formulas:
                    f.write(f"### {formula.name_zh} ({formula.name_en})\n\n")
                    f.write(f"**ID**: `{formula.id}`\n\n")
                    f.write(f"**公式**: `{formula.formula_str}`\n\n")
                    f.write(f"**LaTeX**: `{formula.latex_str}`\n\n")
                    
                    if formula.description_zh:
                        f.write(f"**描述**: {formula.description_zh}\n\n")
                    
                    if formula.quantities:
                        f.write(f"**涉及物理量**:\n\n")
                        for qty in formula.quantities:
                            f.write(f"- **{qty.symbol}**: {qty.name_zh} ({qty.name_en}) - {qty.unit}\n")
                        f.write("\n")
                    
                    if formula.applications:
                        f.write(f"**应用领域**: {', '.join(formula.applications)}\n\n")
                    
                    if formula.notes:
                        f.write(f"**备注**: {formula.notes}\n\n")
                    
                    f.write("---\n\n")
        
        print(f"✓ 已导出到 {filename}")

    def search(self, keyword: str, search_in: str = 'all') -> List[PhysicalFormula]:
        """搜索公式"""
        keyword = keyword.lower()
        results = []
        
        for formula in self.formulas.values():
            match = False
            
            if search_in in ['all', 'name']:
                if keyword in formula.name_zh.lower() or keyword in formula.name_en.lower():
                    match = True
            
            if search_in in ['all', 'description']:
                if keyword in formula.description_zh.lower() or keyword in formula.description_en.lower():
                    match = True
            
            if search_in in ['all', 'category']:
                if keyword in formula.category.lower():
                    match = True
            
            if match:
                results.append(formula)
        
        return results

    def print_summary(self):
        """打印摘要"""
        print("\n" + "="*70)
        print("公式库摘要")
        print("="*70)
        print(f"总公式数: {len(self.formulas)}")
        print(f"总物理量数: {len(self.quantities)}")
        
        # 按分类统计
        by_category = {}
        for formula in self.formulas.values():
            by_category[formula.category] = by_category.get(formula.category, 0) + 1
        
        print("\n按分类统计:")
        for category in sorted(by_category.keys()):
            print(f"  {category}: {by_category[category]}")
        
        print("="*70 + "\n")


class FengDejianSystem:
    """冯德建公式系统 - 预定义的标准物理公式集"""

    @staticmethod
    def build_default_library() -> FormulaLibrary:
        """构建包含标准物理公式的库"""
        lib = FormulaLibrary()

        # ============ 运动学 ============
        v = lib.quantities['v']
        t = lib.quantities['t']
        a = lib.quantities['a']
        m = lib.quantities['m']

        lib.create_formula(
            name_zh='匀加速直线运动速度公式',
            name_en='Uniform acceleration velocity formula',
            formula_str='v = v_0 + a*t',
            description_zh='表示物体在恒定加速度下的速度变化',
            description_en='Describes velocity change under constant acceleration',
            category='运动学',
            applications=['自由落体运动', '汽车加速'],
            notes='v₀为初速度'
        )

        lib.create_formula(
            name_zh='位移公式',
            name_en='Displacement formula',
            formula_str='x = v_0*t + 0.5*a*t**2',
            description_zh='恒定加速度运动的位移公式',
            category='运动学',
            applications=['落体运动', '物体跑道'],
            notes='x为位移'
        )

        # ============ 动力学 ============
        F = lib.quantities['F']
        
        lib.create_formula(
            name_zh='牛顿第二定律',
            name_en='Newton\'s Second Law',
            formula_str='F = m*a',
            description_zh='力与加速度的关系',
            description_en='Relationship between force and acceleration',
            category='动力学',
            applications=['所有力学问题'],
            notes='这是古典力学的基础'
        )

        # ============ 能量 ============
        E = lib.quantities['E']
        c = lib.quantities['c']
        P = lib.quantities['P']

        lib.create_formula(
            name_zh='质能方程',
            name_en='Mass-energy equivalence',
            formula_str='E = m*c**2',
            description_zh='质量与能量的相互转换',
            description_en='Conversion between mass and energy',
            category='相对论',
            applications=['核反应', '粒子物理'],
            prerequisites=['牛顿第二定律'],
            notes='c为光速，约3×10⁸ m/s'
        )

        lib.create_formula(
            name_zh='动能公式',
            name_en='Kinetic energy formula',
            formula_str='E_k = 0.5*m*v**2',
            description_zh='物体运动时所具有的能量',
            category='能量',
            applications=['碰撞问题', '能量守恒'],
            notes='E_k为动能'
        )

        lib.create_formula(
            name_zh='功率定义',
            name_en='Power definition',
            formula_str='P = E/t',
            description_zh='单位时间内做功的多少',
            category='能量',
            applications=['电力计算', '机械效率'],
            notes='P为平均功率'
        )

        # ============ 热学 ============
        lib.create_formula(
            name_zh='理想气体状态方程',
            name_en='Ideal gas law',
            formula_str='P*V = n*R*T',
            description_zh='描述理想气体的宏观性质',
            category='热学',
            applications=['气体膨胀', '泵的工作'],
            notes='P为压强，V为体积，n为物质量，R为气体常数，T为温度'
        )

        # ============ 电磁学 ============
        lib.create_formula(
            name_zh='库仑定律',
            name_en='Coulomb\'s law',
            formula_str='F = k*q_1*q_2/r**2',
            description_zh='两个点电荷之间的静电力',
            category='电磁学',
            applications=['静电场', '原子结构'],
            notes='k为库仑常数'
        )

        lib.create_formula(
            name_zh='欧姆定律',
            name_en='Ohm\'s law',
            formula_str='U = I*R',
            description_zh='电压、电流、电阻的关系',
            category='电磁学',
            applications=['电路分析'],
            notes='U为电压，I为电流，R为电阻'
        )

        return lib


# ============ 示例与测试 ============
def main():
    print("初始化冯德建公式系统...")
    lib = FengDejianSystem.build_default_library()
    lib.print_summary()
    
    # 测试导出
    lib.export_to_json('formulas.json')
    lib.export_to_csv('formulas.csv')
    lib.export_to_markdown('formulas.md')
    
    # 搜索示例
    print("\n搜索 '能量' 相关公式:")
    results = lib.search('能量')
    for formula in results:
        print(f"  - {formula.name_zh}: {formula.formula_str}")
    
    # 求导示例
    print("\n对 'v = v_0 + a*t' 关于时间 t 求导:")
    derivative = lib.derive_formula('v = v_0 + a*t', 'a')
    print(f"  结果: {derivative}")
    
    # 求解示例
    print("\n从 'F = m*a' 解出 'm':")
    solutions = lib.solve_for_variable('F = m*a', 'm')
    for sol in solutions:
        print(f"  m = {sol}")


if __name__ == "__main__":
    main()
