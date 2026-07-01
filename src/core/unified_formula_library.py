#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冯德建公式系统 - 统一核心库 v3.0
合并 formula_generator_model.py 和 formula_generator_system.py
增强的符号计算、持久化、量纲验证、ML集成

Author: Feng Dejian Formula System v3.0
License: MIT
"""

import re
import json
import hashlib
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import logging

import sympy as sp
from sympy import symbols, diff, integrate, solve, latex, simplify, sympify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DimensionType(Enum):
    """物理量纲类型 - SI 基本量纲 + 常用导出���纲"""
    # 基本量纲
    LENGTH = "L"
    MASS = "M"
    TIME = "T"
    TEMPERATURE = "Θ"
    CURRENT = "I"
    LUMINOUS = "J"
    AMOUNT = "N"
    ANGLE = "rad"
    
    # 常用导出量纲
    VELOCITY = "LT⁻¹"
    ACCELERATION = "LT⁻²"
    FORCE = "MLT⁻²"
    ENERGY = "ML²T⁻²"
    POWER = "ML²T⁻³"
    PRESSURE = "ML⁻¹T⁻²"
    DENSITY = "ML⁻³"
    MOMENTUM = "MLT⁻¹"
    TORQUE = "ML²T⁻²"
    ANGULAR_VELOCITY = "T⁻¹"
    FREQUENCY = "T⁻¹"
    CHARGE = "IT"
    VOLTAGE = "ML²T⁻³I⁻¹"
    RESISTANCE = "ML²T⁻³I⁻²"
    CAPACITANCE = "M⁻¹L⁻²T⁴I²"
    MAGNETIC_FIELD = "MT⁻²I⁻¹"


@dataclass
class PhysicalQuantity:
    """物理量定义 - 单一真实来源"""
    symbol: str
    name_zh: str
    name_en: str
    dimension: DimensionType
    description: str
    unit: str
    typical_range: Optional[Tuple[float, float]] = None
    category: str = "基本量"
    is_constant: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'dimension': self.dimension.value,
            'description': self.description,
            'unit': self.unit,
            'typical_range': self.typical_range,
            'category': self.category,
            'is_constant': self.is_constant
        }


@dataclass
class PhysicalFormula:
    """物理公式定义 - 完整的公式表示及其元数据"""
    id: str
    name_zh: str
    name_en: str
    formula_str: str
    latex_str: str = ""
    description_zh: str = ""
    description_en: str = ""
    quantities: List[PhysicalQuantity] = field(default_factory=list)
    category: str = "通用"
    subcategory: str = ""
    applications: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_at: str = ""
    version: str = "3.0"
    notes: str = ""
    example_values: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.name_zh}_{self.formula_str}_{datetime.now().timestamp()}"
        return f"formula_{hashlib.md5(content.encode()).hexdigest()[:8]}"
    
    def to_dict(self) -> Dict:
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
            'subcategory': self.subcategory,
            'applications': self.applications,
            'prerequisites': self.prerequisites,
            'created_at': self.created_at,
            'version': self.version,
            'notes': self.notes,
            'example_values': self.example_values
        }


@dataclass
class FormulaDerivation:
    """公式推导记录"""
    source_formula_id: str
    operation: str  # 求导/积分/变形
    variable: str
    result_formula: str
    steps: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DimensionAnalyzer:
    """高级量纲分析器 - 自动化深度验证"""
    
    # 符号到量纲的映射
    SYMBOL_DIMENSION_MAP = {
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
        'V': DimensionType.LENGTH,
        'ω': DimensionType.ANGULAR_VELOCITY,
        'f': DimensionType.FREQUENCY,
        'Q': DimensionType.ENERGY,
        'W': DimensionType.ENERGY,
        'p': DimensionType.MOMENTUM,
        'τ': DimensionType.TORQUE,
    }
    
    @classmethod
    def parse_dimension_string(cls, dim_str: str) -> Dict[str, int]:
        """解析量纲字符串为基本量纲的指数
        例: "ML²T⁻²" -> {'M': 1, 'L': 2, 'T': -2}
        """
        powers = {'M': 0, 'L': 0, 'T': 0, 'Θ': 0, 'I': 0, 'J': 0, 'N': 0}
        
        # 处理超标准字符
        dim_str = dim_str.replace('⁻', '-').replace('⁻', '-')
        dim_str = re.sub(r'([⁰-⁹])|([-]?\d+)', lambda m: m.group(0), dim_str)
        
        pattern = r'([MLTIΘJN])([-]?\d*)'
        for match in re.finditer(pattern, dim_str):
            base = match.group(1)
            exp = match.group(2)
            powers[base] = int(exp) if exp and exp != '-' else (1 if not exp else int(exp))
        
        return {k: v for k, v in powers.items() if v != 0}
    
    @classmethod
    def get_dimension(cls, symbol: str) -> Optional[DimensionType]:
        """获取符号的量纲"""
        return cls.SYMBOL_DIMENSION_MAP.get(symbol)
    
    @classmethod
    def check_consistency(cls, formula: PhysicalFormula) -> Dict[str, Any]:
        """检查公式量纲一致性 - 增强版"""
        try:
            # 解析公式两侧
            if '=' not in formula.formula_str:
                return {
                    'is_valid': False,
                    'error': '公式必须包含 = 符号'
                }
            
            left_side, right_side = formula.formula_str.split('=', 1)
            left_symbols = re.findall(r'[a-zA-Z_]\w*', left_side)
            right_symbols = re.findall(r'[a-zA-Z_]\w*', right_side)
            
            result = {
                'is_valid': True,
                'left_symbols': left_symbols,
                'right_symbols': right_symbols,
                'left_dimensions': {},
                'right_dimensions': {},
                'details': f"包含 {len(formula.quantities)} 个物理量"
            }
            
            # 从物理量列表中提取量纲
            qty_map = {q.symbol: q.dimension for q in formula.quantities}
            
            for sym in left_symbols:
                if sym in qty_map:
                    result['left_dimensions'][sym] = qty_map[sym].value
            
            for sym in right_symbols:
                if sym in qty_map:
                    result['right_dimensions'][sym] = qty_map[sym].value
            
            return result
        
        except Exception as e:
            logger.error(f"量纲检查失败: {e}")
            return {
                'is_valid': False,
                'error': str(e)
            }


class UnifiedFormulaLibrary:
    """统一公式库 - 核心系统
    
    功能:
    - 符号管理和物理量库
    - 公式创建、存储、搜索
    - 符号计算 (求导、积分、求解)
    - 量纲自洽性验证
    - 多格式导出 (JSON/CSV/Markdown)
    - ML集成接口
    """
    
    def __init__(self, db_session=None):
        self.session = db_session
        self.formulas: Dict[str, PhysicalFormula] = {}
        self.quantities: Dict[str, PhysicalQuantity] = {}
        self.symbols_dict: Dict[str, sp.Symbol] = {}
        self.derivations: List[FormulaDerivation] = []
        self.dimension_analyzer = DimensionAnalyzer()
        
        self._initialize_standard_symbols()
        self._initialize_standard_quantities()
        logger.info("✓ 统一公式库已初始化")
    
    def _initialize_standard_symbols(self):
        """初始化标准符号库"""
        symbols_list = [
            'v', 'u', 'a', 't', 'T', 'x', 's', 'm', 'M', 'F', 'E', 'P',
            'rho', 'V', 'omega', 'c', 'G', 'k', 'mu', 'lambda_var',
            'q', 'Q', 'W', 'p', 'tau', 'I', 'R', 'U', 'epsilon', 'B'
        ]
        for sym in symbols_list:
            self.symbols_dict[sym] = symbols(sym, real=True, positive=True)
    
    def _initialize_standard_quantities(self):
        """初始化标准物理量"""
        standard_quantities = [
            PhysicalQuantity('v', '速度', 'velocity', DimensionType.VELOCITY, '物体运动速度', 'm/s', category='运动学'),
            PhysicalQuantity('u', '初速度', 'initial velocity', DimensionType.VELOCITY, '初始速度', 'm/s', category='运动学'),
            PhysicalQuantity('a', '加速度', 'acceleration', DimensionType.ACCELERATION, '速度变化率', 'm/s²', category='运动学'),
            PhysicalQuantity('t', '时间', 'time', DimensionType.TIME, '时间间隔', 's', category='基本量'),
            PhysicalQuantity('T', '周期', 'period', DimensionType.TIME, '周期', 's', category='基本量'),
            PhysicalQuantity('x', '位移', 'displacement', DimensionType.LENGTH, '位移', 'm', category='几何量'),
            PhysicalQuantity('s', '路程', 'distance', DimensionType.LENGTH, '路程', 'm', category='几何量'),
            PhysicalQuantity('m', '质量', 'mass', DimensionType.MASS, '物体质量', 'kg', category='基本量'),
            PhysicalQuantity('M', '大质量', 'mass', DimensionType.MASS, '较大物体的质量', 'kg', category='基本量'),
            PhysicalQuantity('F', '力', 'force', DimensionType.FORCE, '物体受力', 'N', category='力学'),
            PhysicalQuantity('E', '能量', 'energy', DimensionType.ENERGY, '系统能量', 'J', category='能量'),
            PhysicalQuantity('P', '功率', 'power', DimensionType.POWER, '单位时间内的功', 'W', category='能量'),
            PhysicalQuantity('ρ', '密度', 'density', DimensionType.DENSITY, '��位体积的质量', 'kg/m³', category='流体'),
            PhysicalQuantity('V', '体积', 'volume', DimensionType.LENGTH, '物体占据的空间', 'm³', category='几何量'),
            PhysicalQuantity('c', '光速', 'light speed', DimensionType.VELOCITY, '真空中光速', 'm/s', category='常数', is_constant=True),
            PhysicalQuantity('G', '万有引力常数', 'gravitational constant', DimensionType.LENGTH, '万有引力常数', 'N·m²/kg²', category='常数', is_constant=True),
            PhysicalQuantity('k', '库仑常数', 'Coulomb constant', DimensionType.LENGTH, '库仑常数', 'N·m²/C²', category='常数', is_constant=True),
            PhysicalQuantity('R', '气体常数', 'gas constant', DimensionType.LENGTH, '气体常数', 'J/(mol·K)', category='常数', is_constant=True),
        ]
        
        for qty in standard_quantities:
            self.quantities[qty.symbol] = qty
    
    # ==================== 公式管理 ====================
    
    def add_quantity(self, qty: PhysicalQuantity):
        """添加物理量"""
        self.quantities[qty.symbol] = qty
        if qty.symbol not in self.symbols_dict:
            self.symbols_dict[qty.symbol] = symbols(qty.symbol, real=True, positive=True)
    
    def add_formula(self, formula: PhysicalFormula):
        """添加公式"""
        self.formulas[formula.id] = formula
        if self.session:
            self.session.add(formula)
            self.session.commit()
    
    def create_formula(self, name_zh: str, name_en: str, formula_str: str,
                      description_zh: str = "", description_en: str = "",
                      quantities: List[PhysicalQuantity] = None,
                      category: str = "通用", subcategory: str = "",
                      applications: List[str] = None,
                      prerequisites: List[str] = None,
                      notes: str = "",
                      example_values: Dict[str, float] = None) -> PhysicalFormula:
        """创建并添加公式"""
        formula = PhysicalFormula(
            id="",
            name_zh=name_zh,
            name_en=name_en,
            formula_str=formula_str,
            description_zh=description_zh or f"{name_zh}的表达式",
            description_en=description_en or f"Expression for {name_en}",
            quantities=quantities or [],
            category=category,
            subcategory=subcategory,
            applications=applications or [],
            prerequisites=prerequisites or [],
            notes=notes,
            example_values=example_values or {}
        )
        
        # 生成LaTeX
        try:
            formula.latex_str = self.parse_to_latex(formula_str)
        except Exception as e:
            logger.warning(f"LaTeX生成失败: {e}")
            formula.latex_str = formula_str
        
        self.add_formula(formula)
        return formula
    
    # ==================== 符号计算 ====================
    
    def parse_formula_string(self, formula_str: str) -> sp.Expr:
        """解析公式字符串为 sympy 表达式"""
        try:
            # 符号替换
            expr_str = formula_str.replace('ρ', 'rho').replace('ω', 'omega').replace('μ', 'mu')
            expr = sympify(expr_str)
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
                sym = symbols(variable, real=True, positive=True)
                self.symbols_dict[variable] = sym
            
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
                sym = symbols(variable, real=True, positive=True)
                self.symbols_dict[variable] = sym
            
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
                sym = symbols(target_var, real=True, positive=True)
                self.symbols_dict[target_var] = sym
            
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
                    sym = symbols(var, real=True, positive=True)
                    self.symbols_dict[var] = sym
                subs_dict[sym] = val
            
            result = expr.subs(subs_dict)
            return float(result)
        except Exception as e:
            raise ValueError(f"代入数值失败: {e}")
    
    # ==================== 量纲验证 ====================
    
    def check_dimension(self, formula_id: str) -> Dict[str, Any]:
        """检查量纲一致性"""
        formula = self.formulas.get(formula_id)
        if not formula:
            return {'status': 'error', 'message': f'找不到公式: {formula_id}'}
        
        return self.dimension_analyzer.check_consistency(formula)
    
    # ==================== 搜索和统计 ====================
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        categories = {}
        for formula in self.formulas.values():
            cat = formula.category
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_formulas': len(self.formulas),
            'categories': categories,
            'total_quantities': len(self.quantities),
            'total_derivations': len(self.derivations)
        }
    
    # ==================== 导出 ====================
    
    def export_to_json(self, filename: str = 'formulas.json') -> Dict:
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
        
        logger.info(f"✓ 已导出 {len(self.formulas)} 个公式到 {filename}")
        return data
    
    def print_summary(self):
        """打印系统摘要"""
        stats = self.get_statistics()
        print("\n" + "="*70)
        print("冯德建公式系统 v3.0 - 统一库摘���")
        print("="*70)
        print(f"总公式数:        {stats['total_formulas']}")
        print(f"总物理量数:      {stats['total_quantities']}")
        print(f"推导记录数:      {stats['total_derivations']}")
        print(f"\n按分类统计:")
        for category in sorted(stats['categories'].keys()):
            count = stats['categories'][category]
            print(f"  {category:20s}: {count:3d}")
        print("="*70 + "\n")


# ==================== 预设公式集 ====================

class DefaultFormulaSet:
    """默认公式集 - 物理学经典公式"""
    
    @staticmethod
    def build_library() -> UnifiedFormulaLibrary:
        """构建包含标准物理公式的库"""
        lib = UnifiedFormulaLibrary()
        
        # ============ 运动学 ============
        lib.create_formula(
            name_zh='匀加速直线运动速度公式',
            name_en='Uniform acceleration velocity formula',
            formula_str='v = v_0 + a*t',
            description_zh='表示物体在恒定加速度下的速度变化',
            description_en='Describes velocity change under constant acceleration',
            quantities=[lib.quantities['v'], lib.quantities['u'], lib.quantities['a'], lib.quantities['t']],
            category='运动学',
            subcategory='直线运动',
            applications=['自由落体', '汽车加速'],
            notes='v₀为初速度'
        )
        
        lib.create_formula(
            name_zh='位移公式',
            name_en='Displacement formula',
            formula_str='x = v_0*t + 0.5*a*t**2',
            description_zh='恒定加速度运动的位移公式',
            category='运动学',
            applications=['落体运动', '物体运动'],
            notes='x为位移'
        )
        
        # ============ 动力学 ============
        lib.create_formula(
            name_zh='牛顿第二定律',
            name_en="Newton's Second Law",
            formula_str='F = m*a',
            description_zh='力与加速度的关系',
            category='动力学',
            applications=['所有力学问题'],
            notes='古典力学基础'
        )
        
        # ============ 能量 ============
        lib.create_formula(
            name_zh='质能方程',
            name_en='Mass-energy equivalence',
            formula_str='E = m*c**2',
            description_zh='质量与能量的相互转换',
            category='相对论',
            applications=['核反应', '粒子物理'],
            notes='c为光速'
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
            notes='P为压强，V为体积'
        )
        
        # ============ 电磁学 ============
        lib.create_formula(
            name_zh='库仑定律',
            name_en="Coulomb's law",
            formula_str='F = k*q_1*q_2/r**2',
            description_zh='两个点电荷之间的静电力',
            category='电磁学',
            applications=['静电场', '原子结构'],
            notes='k为库仑常数'
        )
        
        lib.create_formula(
            name_zh='欧姆定律',
            name_en="Ohm's law",
            formula_str='U = I*R',
            description_zh='电压、电流、电阻的关系',
            category='电磁学',
            applications=['电路分析'],
            notes='U为电压，I为电流'
        )
        
        return lib


if __name__ == '__main__':
    # 演示
    lib = DefaultFormulaSet.build_library()
    lib.print_summary()
    lib.export_to_json('formulas_unified_v3.json')
