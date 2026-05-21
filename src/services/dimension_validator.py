"""
深度量纲验证系统 - 自动检查公式的物理量纲一致性
支持完整的多变量量纲分析和错误诊断
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re
from enum import Enum


class DimensionBase(str, Enum):
    """基本量纲"""
    LENGTH = "L"
    MASS = "M"
    TIME = "T"
    TEMPERATURE = "Θ"
    CURRENT = "I"
    LUMINOUS = "J"
    AMOUNT = "N"


class ExpressionParser:
    """表达式解析器 - 从公式字符串中提取符号和操作"""
    
    @staticmethod
    def parse_expression(expr_str: str) -> Dict[str, int]:
        """解析表达式，返回每个符号出现的总量纲
        
        例如：
            "m * c**2" -> {"m": 1, "c": 2}
            "F / (m*a)" -> {"F": 1, "m": -1, "a": -1}
        """
        symbols = {}
        
        # 移除空格
        expr_str = expr_str.replace(' ', '')
        
        # 处理除法和乘法
        # 将除法转换为乘以倒数
        expr_str = expr_str.replace('/', '*').replace('**-', '**(-')
        
        # 提取所有符号及其幂次
        pattern = r'([a-zA-Z_]\w*)(?:\*\*([^*]+))?'
        
        for match in re.finditer(pattern, expr_str):
            symbol = match.group(1)
            power_str = match.group(2)
            
            # 计算幂次
            power = 1
            if power_str:
                try:
                    # 处理括号和负数
                    power_str = power_str.strip('()')
                    power = int(power_str)
                except:
                    power = 1
            
            symbols[symbol] = symbols.get(symbol, 0) + power
        
        return symbols


@dataclass
class DimensionVector:
    """量纲向量 - 表示一个物理量的量纲"""
    L: int = 0  # 长度
    M: int = 0  # 质量
    T: int = 0  # 时间
    Θ: int = 0  # 温度
    I: int = 0  # 电流
    J: int = 0  # 光强
    N: int = 0  # 物质量
    
    def __eq__(self, other: 'DimensionVector') -> bool:
        """检查两个量纲是否相等"""
        return (self.L == other.L and self.M == other.M and 
                self.T == other.T and self.Θ == other.Θ and
                self.I == other.I and self.J == other.J and
                self.N == other.N)
    
    def __mul__(self, other: 'DimensionVector') -> 'DimensionVector':
        """两个量纲相乘"""
        return DimensionVector(
            L=self.L + other.L,
            M=self.M + other.M,
            T=self.T + other.T,
            Θ=self.Θ + other.Θ,
            I=self.I + other.I,
            J=self.J + other.J,
            N=self.N + other.N
        )
    
    def __truediv__(self, other: 'DimensionVector') -> 'DimensionVector':
        """两个量纲相除"""
        return DimensionVector(
            L=self.L - other.L,
            M=self.M - other.M,
            T=self.T - other.T,
            Θ=self.Θ - other.Θ,
            I=self.I - other.I,
            J=self.J - other.J,
            N=self.N - other.N
        )
    
    def __pow__(self, power: int) -> 'DimensionVector':
        """量纲的幂次"""
        return DimensionVector(
            L=self.L * power,
            M=self.M * power,
            T=self.T * power,
            Θ=self.Θ * power,
            I=self.I * power,
            J=self.J * power,
            N=self.N * power
        )
    
    def to_string(self) -> str:
        """将量纲向量转换为字符串表示"""
        components = []
        
        for base, power in [
            ('M', self.M), ('L', self.L), ('T', self.T),
            ('Θ', self.Θ), ('I', self.I), ('J', self.J), ('N', self.N)
        ]:
            if power > 0:
                if power == 1:
                    components.append(base)
                else:
                    components.append(f"{base}^{power}")
            elif power < 0:
                if power == -1:
                    components.append(f"{base}^-1")
                else:
                    components.append(f"{base}^{power}")
        
        return '·'.join(components) if components else '无量纲'


class DimensionDatabase:
    """量纲数据库 - 存储已知符号的量纲信息"""
    
    # 基础物理量的量纲定义
    DIMENSION_MAP = {
        # 基本量
        'm': DimensionVector(M=1),      # 质量
        'M': DimensionVector(M=1),      # 质量
        't': DimensionVector(T=1),      # 时间
        'T': DimensionVector(T=1),      # 时间
        'x': DimensionVector(L=1),      # 位移
        's': DimensionVector(L=1),      # 路程
        'l': DimensionVector(L=1),      # 长度
        
        # 导出量 - 力学
        'v': DimensionVector(L=1, T=-1),           # 速度
        'u': DimensionVector(L=1, T=-1),           # 初速度
        'a': DimensionVector(L=1, T=-2),           # 加速度
        'F': DimensionVector(M=1, L=1, T=-2),      # 力
        'p': DimensionVector(M=1, L=1, T=-1),      # 动量
        'E': DimensionVector(M=1, L=2, T=-2),      # 能量
        'P': DimensionVector(M=1, L=2, T=-3),      # 功率
        'W': DimensionVector(M=1, L=2, T=-2),      # 功
        
        # 导出量 - 流体力学
        'ρ': DimensionVector(M=1, L=-3),           # 密度
        'V': DimensionVector(L=3),                 # 体积
        'ν': DimensionVector(L=2, T=-1),           # 运动粘度
        'η': DimensionVector(M=1, L=-1, T=-1),     # 动力粘度
        
        # 导出量 - 热学
        'Q': DimensionVector(M=1, L=2, T=-2),      # 热量
        'c': DimensionVector(L=2, T=-2, Θ=-1),     # 比热容
        'S': DimensionVector(M=1, L=2, T=-2, Θ=-1), # 熵
        
        # 常数
        'c_light': DimensionVector(L=1, T=-1),     # 光速
        'G': DimensionVector(L=3, M=-1, T=-2),     # 万有引力常数
        'k_B': DimensionVector(M=1, L=2, T=-2, Θ=-1), # 玻尔兹曼常数
        'h': DimensionVector(M=1, L=2, T=-1),      # 普朗克常数
        'e': DimensionVector(I=1, T=1),            # 基本电荷
        
        # 无量纲量
        'n': DimensionVector(),                    # 数量
        'η_eff': DimensionVector(),                # 效率
    }
    
    @staticmethod
    def get_dimension(symbol: str) -> Optional[DimensionVector]:
        """获取符号的量纲"""
        return DimensionDatabase.DIMENSION_MAP.get(symbol)
    
    @staticmethod
    def is_dimensionless(symbol: str) -> bool:
        """检查是否为无量纲量"""
        dim = DimensionDatabase.get_dimension(symbol)
        if dim is None:
            return False
        return dim == DimensionVector()


class DeepDimensionValidator:
    """深度量纲验证器 - 完整的量纲分析和错误诊断"""
    
    def __init__(self):
        self.dimension_db = DimensionDatabase()
        self.parser = ExpressionParser()
    
    def validate_formula(self, formula_str: str) -> Dict[str, Any]:
        """验证公式的量纲一致性
        
        Args:
            formula_str: 公式字符串 (e.g., "E = m*c**2")
        
        Returns:
            详细的验证结果
        """
        try:
            # 1. 分离左右两边
            if '=' not in formula_str:
                return self._error_result('公式格式错误：缺少等号')
            
            left_str, right_str = formula_str.split('=', 1)
            left_str = left_str.strip()
            right_str = right_str.strip()
            
            # 2. 分析左右两边的符号
            left_symbols = self.parser.parse_expression(left_str)
            right_symbols = self.parser.parse_expression(right_str)
            
            # 3. 计算左右两边的量纲
            left_dimension = self._calculate_dimension(left_symbols)
            right_dimension = self._calculate_dimension(right_symbols)
            
            # 4. 对比量纲
            is_consistent = left_dimension == right_dimension
            
            # 5. 检查未定义的符号
            undefined_symbols = self._find_undefined_symbols(
                set(left_symbols.keys()) | set(right_symbols.keys())
            )
            
            # 6. 生成诊断报告
            return {
                'is_consistent': is_consistent,
                'match_percentage': 100.0 if is_consistent else 0.0,
                'left_side': {
                    'expression': left_str,
                    'symbols': left_symbols,
                    'dimension': left_dimension.to_string(),
                    'dimension_vector': self._vector_to_dict(left_dimension)
                },
                'right_side': {
                    'expression': right_str,
                    'symbols': right_symbols,
                    'dimension': right_dimension.to_string(),
                    'dimension_vector': self._vector_to_dict(right_dimension)
                },
                'undefined_symbols': undefined_symbols,
                'diagnosis': self._generate_diagnosis(
                    left_dimension, right_dimension, undefined_symbols
                )
            }
        
        except Exception as e:
            return self._error_result(str(e))
    
    def _calculate_dimension(self, symbols_dict: Dict[str, int]) -> DimensionVector:
        """根据符号字典计算总量纲"""
        result = DimensionVector()
        
        for symbol, power in symbols_dict.items():
            dim = self.dimension_db.get_dimension(symbol)
            
            if dim is None:
                # 未定义的符号，暂时跳过
                continue
            
            # 应用幂次
            dim_powered = dim ** power
            
            # 累乘
            result = result * dim_powered
        
        return result
    
    def _find_undefined_symbols(self, symbols: set) -> List[str]:
        """找出所有未定义的符号"""
        undefined = []
        
        for symbol in symbols:
            if self.dimension_db.get_dimension(symbol) is None:
                undefined.append(symbol)
        
        return undefined
    
    def _generate_diagnosis(self,
                           left_dim: DimensionVector,
                           right_dim: DimensionVector,
                           undefined_symbols: List[str]) -> Dict[str, Any]:
        """生成诊断报告"""
        diagnosis = {
            'status': 'OK',
            'messages': []
        }
        
        # 检查未定义的符号
        if undefined_symbols:
            diagnosis['status'] = 'WARNING'
            diagnosis['messages'].append(
                f"存在未定义的符号: {', '.join(undefined_symbols)}. "
                "请在 DimensionDatabase 中添加这些符号的量纲定义。"
            )
        
        # 检查量纲不匹配
        if left_dim != right_dim:
            diagnosis['status'] = 'ERROR'
            
            # 生成详细的错误信息
            diff_components = []
            for base in ['M', 'L', 'T', 'Θ', 'I', 'J', 'N']:
                left_val = getattr(left_dim, base, 0)
                right_val = getattr(right_dim, base, 0)
                
                if left_val != right_val:
                    diff_components.append(
                        f"{base}: 左侧={left_val}, 右侧={right_val}"
                    )
            
            diagnosis['messages'].append(
                f"量纲不匹配：" + " | ".join(diff_components)
            )
        else:
            diagnosis['messages'].append("✓ 公式量纲一致")
        
        return diagnosis
    
    def _vector_to_dict(self, vec: DimensionVector) -> Dict[str, int]:
        """将量纲向量转换为字典"""
        return {
            'M': vec.M,
            'L': vec.L,
            'T': vec.T,
            'Θ': vec.Θ,
            'I': vec.I,
            'J': vec.J,
            'N': vec.N
        }
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """生成错误结果"""
        return {
            'is_consistent': False,
            'match_percentage': 0.0,
            'error': error_msg,
            'diagnosis': {
                'status': 'ERROR',
                'messages': [error_msg]
            }
        }


# 使用示例
if __name__ == "__main__":
    validator = DeepDimensionValidator()
    
    # 测试有效的公式
    print("测试 1: E = m*c**2")
    result = validator.validate_formula("E = m*c**2")
    print(f"一致性: {result['is_consistent']}")
    print(f"诊断: {result['diagnosis']}\n")
    
    # 测试无效的公式
    print("测试 2: F = m + a")
    result = validator.validate_formula("F = m + a")
    print(f"一致性: {result['is_consistent']}")
    print(f"诊断: {result['diagnosis']}\n")
    
    # 测试包含未定义符号的公式
    print("测试 3: E = m*x**2")
    result = validator.validate_formula("E = m*x**2")
    print(f"一致性: {result['is_consistent']}")
    if result.get('undefined_symbols'):
        print(f"未定义符号: {result['undefined_symbols']}")
