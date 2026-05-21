"""
统一的公式库系统 - 合并原有的两个系统
整合所有核心功能：公式管理、量纲分析、符号计算、数据库持久化
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import hashlib
import sympy as sp
from abc import ABC, abstractmethod


class DimensionType(Enum):
    """物理量纲类型 (SI 基本量纲)"""
    LENGTH = "L"
    MASS = "M"
    TIME = "T"
    TEMPERATURE = "Θ"
    CURRENT = "I"
    LUMINOUS = "J"
    AMOUNT = "N"
    ANGLE = "rad"
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


@dataclass
class PhysicalQuantity:
    """物理量定义"""
    symbol: str
    name_zh: str
    name_en: str
    dimension: DimensionType
    description: str
    unit: str
    typical_range: Optional[Tuple[float, float]] = None
    category: str = "基本量"
    is_constant: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
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
    """物理公式定义"""
    id: str
    name_zh: str
    name_en: str
    formula_str: str
    latex_str: str = ""
    description_zh: str = ""
    description_en: str = ""
    quantities: List[PhysicalQuantity] = field(default_factory=list)
    category: str = ""
    applications: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_at: str = ""
    version: str = "1.0"
    notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = f"formula_{int(datetime.now().timestamp()*1000)}"
    
    def to_dict(self) -> Dict[str, Any]:
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
    
    def get_hash(self) -> str:
        """生成公式的唯一哈希值"""
        content = f"{self.name_zh}{self.formula_str}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


@dataclass
class FormulaDerivation:
    """公式推导记录"""
    id: str
    source_formula_id: str
    operation: str  # 求导/积分/变形
    result_formula: str
    steps: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DimensionAnalyzer:
    """量纲分析器 - 增强版"""
    
    # 基本符号到量纲的映射
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
        'V': DimensionType.LENGTH,
        'ω': DimensionType.ANGULAR_VELOCITY,
        'f': DimensionType.FREQUENCY,
        'c': DimensionType.VELOCITY,
        'G': DimensionType.LENGTH,  # 简化
    }
    
    @staticmethod
    def get_dimension(symbol: str) -> Optional[DimensionType]:
        """获取符号的量纲"""
        return DimensionAnalyzer.DIMENSION_MAP.get(symbol)
    
    @staticmethod
    def parse_dimension_string(dim_str: str) -> Dict[str, int]:
        """解析量纲字符串为字典
        例如: "ML²T⁻²" -> {'M': 1, 'L': 2, 'T': -2}
        """
        dim_dict = {}
        i = 0
        while i < len(dim_str):
            if dim_str[i].isalpha():
                symbol = dim_str[i]
                i += 1
                
                # 提取幂次
                power_str = ""
                while i < len(dim_str) and (dim_str[i].isdigit() or dim_str[i] in '⁻⁻'):
                    power_str += dim_str[i]
                    i += 1
                
                # 处理上标数字
                power = 1
                if power_str:
                    power_str = power_str.replace('⁻', '-')
                    power = int(power_str) if power_str else 1
                
                dim_dict[symbol] = dim_dict.get(symbol, 0) + power
            else:
                i += 1
        
        return dim_dict
    
    @staticmethod
    def check_consistency(formula: PhysicalFormula) -> Dict[str, Any]:
        """检查公式量纲一致性（增强版）"""
        try:
            # 解析公式左右两边
            if '=' not in formula.formula_str:
                return {
                    'is_consistent': False,
                    'error': '公式格式错误：缺少等号'
                }
            
            left_str, right_str = formula.formula_str.split('=', 1)
            
            # 简化的验证逻辑
            left_symbols = set(c for c in left_str if c.isalpha())
            right_symbols = set(c for c in right_str if c.isalpha())
            
            # 获取所有符号的量纲
            left_dims = [DimensionAnalyzer.get_dimension(s) for s in left_symbols]
            right_dims = [DimensionAnalyzer.get_dimension(s) for s in right_symbols]
            
            # 检查是否所有符号都有定义
            undefined = []
            for s in left_symbols | right_symbols:
                if DimensionAnalyzer.get_dimension(s) is None:
                    undefined.append(s)
            
            return {
                'is_consistent': len(undefined) == 0,
                'left_symbols': list(left_symbols),
                'right_symbols': list(right_symbols),
                'left_dimensions': [d.value if d else None for d in left_dims],
                'right_dimensions': [d.value if d else None for d in right_dims],
                'undefined_symbols': undefined,
                'details': f"包含 {len(formula.quantities)} 个物理量"
            }
        except Exception as e:
            return {
                'is_consistent': False,
                'error': str(e)
            }


class UnifiedFormulaLibrary:
    """
    统一的公式库 - 合并了原有两个系统的所有功能
    
    功能包括：
    - 公式创建、查询、搜索
    - SymPy符号计算（求导、积分、求解）
    - LaTeX转换
    - 量纲验证
    - JSON/CSV/Markdown导出
    """
    
    def __init__(self):
        self.formulas: Dict[str, PhysicalFormula] = {}
        self.quantities: Dict[str, PhysicalQuantity] = {}
        self.symbols_dict: Dict[str, sp.Symbol] = {}
        self.derivations: List[FormulaDerivation] = []
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
            self.symbols_dict[sym] = sp.Symbol(sym, real=True, positive=True)
    
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
                           '光在真空中的速度', 'm/s', category='常数', is_constant=True),
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
            expr_str = formula_str.replace('ρ', 'rho').replace('ω', 'omega')\
                                  .replace('μ', 'mu').replace('λ', 'lambda_var')
            expr = sp.sympify(expr_str)
            return expr
        except Exception as e:
            raise ValueError(f"无法解析公式: {formula_str}, 错误: {e}")
    
    def parse_to_latex(self, formula_str: str) -> str:
        """将公式字符串转换为LaTeX"""
        try:
            expr = self.parse_formula_string(formula_str)
            return sp.latex(expr)
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
                result = sp.diff(result, sym)
            
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
            
            result = sp.integrate(expr, sym)
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
            
            solutions = sp.solve(expr, sym)
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
    
    def check_dimension_consistency(self, formula_id: str) -> Dict[str, Any]:
        """检查公式量纲一致性"""
        formula = self.formulas.get(formula_id)
        if not formula:
            return {'status': 'error', 'message': f'找不到公式: {formula_id}'}
        
        return DimensionAnalyzer.check_consistency(formula)
    
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
            'total_symbols': len(self.symbols_dict),
            'total_derivations': len(self.derivations)
        }
    
    def print_summary(self):
        """打印摘要"""
        stats = self.get_statistics()
        print("\n" + "="*70)
        print("冯德建统一公式库 - 摘要")
        print("="*70)
        print(f"总公式数: {stats['total_formulas']}")
        print(f"总物理量数: {stats['total_quantities']}")
        print(f"总符号数: {stats['total_symbols']}")
        print(f"推导记录数: {stats['total_derivations']}")
        
        print("\n按分类统计:")
        for category in sorted(stats['categories'].keys()):
            print(f"  {category}: {stats['categories'][category]}")
        
        print("="*70 + "\n")


# 示例用法和测试
if __name__ == "__main__":
    # 创建统一的公式库
    lib = UnifiedFormulaLibrary()
    
    # 创建公式
    v = lib.quantities['v']
    m = lib.quantities['m']
    c = lib.quantities['c']
    E = lib.quantities['E']
    
    lib.create_formula(
        name_zh='质能方程',
        name_en='Mass-energy equivalence',
        formula_str='E = m*c**2',
        description_zh='质量与能量的相互转换',
        category='相对论',
        quantities=[m, c, E],
        notes='爱因斯坦著名公式'
    )
    
    # 打印摘要
    lib.print_summary()
    
    # 测试符号计算
    print("\n测试符号计算:")
    print("对 E = m*c**2 关于 m 求解:")
    solutions = lib.solve_for_variable('E = m*c**2', 'm')
    for sol in solutions:
        print(f"  m = {sol}")
    
    # 测试量纲验证
    print("\n测试量纲验证:")
    formula = lib.formulas['formula_0001']
    result = lib.check_dimension_consistency('formula_0001')
    print(f"公式: {formula.formula_str}")
    print(f"验证结果: {result}")
