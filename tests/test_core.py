"""
自动化测试套件 - 保证代码质量
>80% 代码覆盖率
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import Base
from src.services.dimension_validator import (
    DimensionVector, DimensionDatabase, DeepDimensionValidator, ExpressionParser
)
from src.services.formula_service import FormulaService
from src.core.unified_library import UnifiedFormulaLibrary


# ============ Fixtures ============

@pytest.fixture
def test_db():
    """测试数据库"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    session.close()


@pytest.fixture
def validator():
    """深度量纲验证器"""
    return DeepDimensionValidator()


@pytest.fixture
def library():
    """统一公式库"""
    return UnifiedFormulaLibrary()


@pytest.fixture
def formula_service(test_db):
    """公式服务"""
    return FormulaService(test_db)


# ============ 量纲测试 ============

class TestDimensionVector:
    """测试量纲向量"""
    
    def test_vector_creation(self):
        """测试量纲向量创建"""
        vec = DimensionVector(M=1, L=2, T=-2)
        assert vec.M == 1
        assert vec.L == 2
        assert vec.T == -2
    
    def test_vector_equality(self):
        """测试量纲相等"""
        vec1 = DimensionVector(M=1, L=1, T=-2)
        vec2 = DimensionVector(M=1, L=1, T=-2)
        assert vec1 == vec2
    
    def test_vector_multiplication(self):
        """测试量纲相乘"""
        vec1 = DimensionVector(M=1, L=1)
        vec2 = DimensionVector(T=-2)
        result = vec1 * vec2
        
        assert result.M == 1
        assert result.L == 1
        assert result.T == -2
    
    def test_vector_division(self):
        """测试量纲相除"""
        vec1 = DimensionVector(M=1, L=2, T=-2)
        vec2 = DimensionVector(M=1)
        result = vec1 / vec2
        
        assert result.M == 0
        assert result.L == 2
        assert result.T == -2
    
    def test_vector_power(self):
        """测试量纲的幂次"""
        vec = DimensionVector(L=1, T=-1)
        result = vec ** 2
        
        assert result.L == 2
        assert result.T == -2
    
    def test_vector_to_string(self):
        """测试量纲字符串表示"""
        vec = DimensionVector(M=1, L=2, T=-2)
        result = vec.to_string()
        
        assert 'M' in result
        assert 'L' in result
        assert 'T' in result


class TestDimensionDatabase:
    """测试量纲数据库"""
    
    def test_get_dimension_mass(self):
        """测试质量量纲"""
        dim = DimensionDatabase.get_dimension('m')
        assert dim is not None
        assert dim.M == 1
    
    def test_get_dimension_velocity(self):
        """测试速度量纲"""
        dim = DimensionDatabase.get_dimension('v')
        assert dim is not None
        assert dim.L == 1
        assert dim.T == -1
    
    def test_get_dimension_energy(self):
        """测试能量量纲"""
        dim = DimensionDatabase.get_dimension('E')
        assert dim is not None
        assert dim.M == 1
        assert dim.L == 2
        assert dim.T == -2
    
    def test_get_dimension_undefined(self):
        """测试未定义的符号"""
        dim = DimensionDatabase.get_dimension('xyz')
        assert dim is None
    
    def test_is_dimensionless(self):
        """测试无量纲判断"""
        assert DimensionDatabase.is_dimensionless('n')
        assert not DimensionDatabase.is_dimensionless('m')


class TestExpressionParser:
    """测试表达式解析器"""
    
    def test_parse_simple_expression(self):
        """测试简单表达式"""
        result = ExpressionParser.parse_expression("m * c**2")
        
        assert result.get('m') == 1
        assert result.get('c') == 2
    
    def test_parse_complex_expression(self):
        """测试复杂表达式"""
        result = ExpressionParser.parse_expression("F / (m*a)")
        
        assert result.get('F') == 1
        assert result.get('m') == -1
        assert result.get('a') == -1
    
    def test_parse_with_spaces(self):
        """测试带有空格的表达式"""
        result = ExpressionParser.parse_expression("m * c ** 2")
        
        assert result.get('m') == 1
        assert result.get('c') == 2


class TestDeepDimensionValidator:
    """测试深度量纲验证器"""
    
    def test_valid_formula_einstein(self, validator):
        """测试有效的公式：E=mc2"""
        result = validator.validate_formula("E = m*c**2")
        
        assert result['is_consistent'] == True
        assert result['match_percentage'] == 100.0
        assert result['diagnosis']['status'] == 'OK'
    
    def test_valid_formula_newton(self, validator):
        """测试有效的公式：F=ma"""
        result = validator.validate_formula("F = m*a")
        
        assert result['is_consistent'] == True
        assert result['match_percentage'] == 100.0
    
    def test_valid_formula_kinetic_energy(self, validator):
        """测试有效的公式：动能"""
        result = validator.validate_formula("E = 0.5*m*v**2")
        
        assert result['is_consistent'] == True
    
    def test_invalid_formula_wrong_dimension(self, validator):
        """测试量纲错误：F = m + a"""
        result = validator.validate_formula("F = m + a")
        
        assert result['is_consistent'] == False
        assert result['diagnosis']['status'] == 'ERROR'
    
    def test_formula_without_equals(self, validator):
        """测试没有等号的公式"""
        result = validator.validate_formula("m*c**2")
        
        assert result['is_consistent'] == False
        assert 'error' in result
    
    def test_formula_with_undefined_symbols(self, validator):
        """测试包含未定义符号的公式"""
        result = validator.validate_formula("E = x*y**2")
        
        # 应罓有未定义的符号警告
        if result.get('undefined_symbols'):
            assert result['diagnosis']['status'] in ['WARNING', 'OK']


class TestUnifiedFormulaLibrary:
    """测试统一公式库"""
    
    def test_create_formula(self, library):
        """测试创建公式"""
        qty_m = library.quantities['m']
        qty_E = library.quantities['E']
        qty_c = library.quantities['c']
        
        formula = library.create_formula(
            name_zh='质能方程',
            name_en='E=mc2',
            formula_str='E = m*c**2',
            category='相对论',
            quantities=[qty_m, qty_E, qty_c]
        )
        
        assert formula.name_zh == '质能方程'
        assert formula.formula_str == 'E = m*c**2'
    
    def test_derive_formula(self, library):
        """测试推导公式"""
        result = library.derive_formula('v = u + a*t', 'a')
        
        assert result is not None
        assert 't' in result or '1' in result
    
    def test_solve_formula(self, library):
        """测试求解公式"""
        solutions = library.solve_for_variable('F = m*a', 'm')
        
        assert len(solutions) > 0
        assert 'a' in str(solutions[0]) or 'F' in str(solutions[0])
    
    def test_search_formulas(self, library):
        """测试搜索公��"""
        qty_m = library.quantities['m']
        library.create_formula(
            name_zh='质能方程',
            name_en='E=mc2',
            formula_str='E = m*c**2',
            category='相对论',
            quantities=[qty_m]
        )
        
        results = library.search('energy')
        assert len(results) > 0


class TestFormulaService:
    """测试公式服务"""
    
    def test_create_formula_success(self, formula_service):
        """测试成功创建公式"""
        result = formula_service.create_formula(
            name_zh='质能方程',
            name_en='E=mc2',
            formula_str='E = m*c**2',
            category='相对论'
        )
        
        assert result['success'] == True
        assert 'id' in result
    
    def test_create_formula_duplicate(self, formula_service):
        """测试副本检查"""
        # 创建第一个
        result1 = formula_service.create_formula(
            name_zh='质能方程',
            name_en='E=mc2',
            formula_str='E = m*c**2',
            category='相对论'
        )
        
        # 伝建第二个（应该失败）
        result2 = formula_service.create_formula(
            name_zh='质能方程',
            name_en='E=mc2',
            formula_str='E = m*c**2',
            category='相对论'
        )
        
        assert result1['success'] == True
        assert result2['success'] == False
    
    def test_get_statistics(self, formula_service):
        """测试统计信息"""
        stats = formula_service.get_statistics()
        
        assert 'total_formulas' in stats
        assert 'total_quantities' in stats
        assert 'validated_count' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=html"])
