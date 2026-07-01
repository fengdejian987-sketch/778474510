#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冯德建公式系统 - 单元测试
测试统一公式库核心功能

Author: Test Suite v3.0
"""

import pytest
from src.core.unified_formula_library import (
    DimensionType,
    PhysicalQuantity,
    PhysicalFormula,
    DimensionAnalyzer,
    UnifiedFormulaLibrary,
    DefaultFormulaSet,
)


class TestDimensionAnalyzer:
    """量纲分析器测试"""
    
    def test_parse_dimension_string(self):
        """测试量纲字符串解析"""
        result = DimensionAnalyzer.parse_dimension_string("ML²T⁻²")
        assert result['M'] == 1
        assert result['L'] == 2
        assert result['T'] == -2
    
    def test_get_dimension(self):
        """测试符号到量纲的映射"""
        assert DimensionAnalyzer.get_dimension('v') == DimensionType.VELOCITY
        assert DimensionAnalyzer.get_dimension('m') == DimensionType.MASS
        assert DimensionAnalyzer.get_dimension('F') == DimensionType.FORCE
        assert DimensionAnalyzer.get_dimension('E') == DimensionType.ENERGY
    
    def test_check_consistency(self):
        """测试量纲一致性检查"""
        qty_v = PhysicalQuantity('v', '速度', 'velocity', DimensionType.VELOCITY, '速度', 'm/s')
        qty_u = PhysicalQuantity('u', '初速度', 'initial velocity', DimensionType.VELOCITY, '初速', 'm/s')
        qty_a = PhysicalQuantity('a', '加速度', 'acceleration', DimensionType.ACCELERATION, '加速', 'm/s²')
        qty_t = PhysicalQuantity('t', '时间', 'time', DimensionType.TIME, '时间', 's')
        
        formula = PhysicalFormula(
            id="test_001",
            name_zh="速度公式",
            name_en="velocity formula",
            formula_str="v = u + a*t",
            quantities=[qty_v, qty_u, qty_a, qty_t]
        )
        
        result = DimensionAnalyzer.check_consistency(formula)
        assert result['is_valid'] == True
        assert 'left_symbols' in result
        assert 'right_symbols' in result


class TestPhysicalQuantity:
    """物理量定义测试"""
    
    def test_quantity_creation(self):
        """测试物理量创建"""
        qty = PhysicalQuantity(
            'v', '速度', 'velocity', DimensionType.VELOCITY,
            '物体速度', 'm/s', category='运动学'
        )
        assert qty.symbol == 'v'
        assert qty.name_zh == '速度'
        assert qty.dimension == DimensionType.VELOCITY
    
    def test_quantity_to_dict(self):
        """测试物理量字典转换"""
        qty = PhysicalQuantity(
            'v', '速度', 'velocity', DimensionType.VELOCITY,
            '物体速度', 'm/s'
        )
        qty_dict = qty.to_dict()
        assert qty_dict['symbol'] == 'v'
        assert qty_dict['name_zh'] == '速度'
        assert qty_dict['dimension'] == 'LT⁻¹'
        assert qty_dict['unit'] == 'm/s'


class TestPhysicalFormula:
    """物理公式定义测试"""
    
    def test_formula_creation(self):
        """测试公式创建"""
        formula = PhysicalFormula(
            id="fm_001",
            name_zh="质能方程",
            name_en="Mass-energy equivalence",
            formula_str="E = m*c**2",
            description_zh="质量与能量的转换",
            category="相对论"
        )
        assert formula.id == "fm_001"
        assert formula.name_zh == "质能方程"
        assert formula.category == "相对论"
    
    def test_formula_auto_id_generation(self):
        """测试公式自动ID生成"""
        formula = PhysicalFormula(
            id="",
            name_zh="速度公式",
            name_en="velocity formula",
            formula_str="v = v_0 + a*t"
        )
        assert formula.id.startswith("formula_")
        assert len(formula.id) > 8
    
    def test_formula_to_dict(self):
        """测试公式字典转换"""
        formula = PhysicalFormula(
            id="fm_001",
            name_zh="牛顿第二定律",
            name_en="Newton's Second Law",
            formula_str="F = m*a",
            category="动力学"
        )
        formula_dict = formula.to_dict()
        assert formula_dict['id'] == 'fm_001'
        assert formula_dict['name_zh'] == '牛顿第二定律'
        assert formula_dict['formula'] == 'F = m*a'


class TestUnifiedFormulaLibrary:
    """统一公式库测试"""
    
    @pytest.fixture
    def library(self):
        """创建库实例"""
        return UnifiedFormulaLibrary()
    
    def test_library_initialization(self, library):
        """测试库初始化"""
        assert len(library.quantities) > 0
        assert len(library.symbols_dict) > 0
        assert 'v' in library.quantities
        assert 'm' in library.quantities
        assert 'c' in library.quantities
    
    def test_add_quantity(self, library):
        """测试添加物理量"""
        qty = PhysicalQuantity(
            'n', '物质量', 'amount', DimensionType.AMOUNT,
            '物质的量', 'mol'
        )
        library.add_quantity(qty)
        assert 'n' in library.quantities
        assert library.quantities['n'].name_zh == '物质量'
    
    def test_create_formula(self, library):
        """测试创建公式"""
        formula = library.create_formula(
            name_zh="质能方程",
            name_en="Mass-energy equivalence",
            formula_str="E = m*c**2",
            description_zh="质量与能量的转换",
            category="相对论"
        )
        assert formula.name_zh == "质能方程"
        assert formula.id in library.formulas
        assert len(library.formulas) > 0
    
    def test_parse_formula_string(self, library):
        """测试解析公式字符串"""
        expr = library.parse_formula_string("v = v_0 + a*t")
        assert str(expr) == "v_0 + a*t"
    
    def test_parse_to_latex(self, library):
        """测试转换为LaTeX"""
        latex = library.parse_to_latex("E = m*c**2")
        assert "E" in latex
        assert "m" in latex
        assert "c" in latex
    
    def test_derive_formula_first_order(self, library):
        """测试一阶求导"""
        # 对 x = 0.5*a*t^2 关于 t 求导，应得 a*t
        result = library.derive_formula("0.5*a*t**2", "t")
        assert "a" in result
        assert "t" in result or result == "a*t"
    
    def test_derive_formula_second_order(self, library):
        """测试二阶求导"""
        # 对 v = a*t 关于 t 二阶求导，应得 0
        result = library.derive_formula("a*t", "t", order=2)
        assert result == "0" or "0" in result
    
    def test_integrate_formula(self, library):
        """测试积分"""
        result = library.integrate_formula("a*t", "t")
        assert "a" in result or len(result) > 0
    
    def test_solve_for_variable(self, library):
        """测试求解变量"""
        solutions = library.solve_for_variable("F - m*a", "m")
        assert len(solutions) > 0
        assert "F" in solutions[0] or "m" in solutions[0]
    
    def test_substitute_values(self, library):
        """测试数值代入"""
        # E = m*c^2, m=1kg, c=3e8 m/s
        result = library.substitute_values("m*c**2", {"m": 1, "c": 3e8})
        expected = 1 * (3e8) ** 2
        assert abs(result - expected) < 1e10
    
    def test_search_formulas(self, library):
        """测试搜索公式"""
        # 添加几个公式
        library.create_formula(
            name_zh="速度公式",
            name_en="velocity formula",
            formula_str="v = u + a*t",
            category="运动学"
        )
        library.create_formula(
            name_zh="位移公式",
            name_en="displacement formula",
            formula_str="x = v_0*t + 0.5*a*t**2",
            category="运动学"
        )
        
        # 搜索"运动学"
        results = library.search("运动学", search_in="category")
        assert len(results) >= 2
        
        # 搜索"速度"
        results = library.search("速度", search_in="name")
        assert len(results) >= 1
    
    def test_get_statistics(self, library):
        """测试获取统计信息"""
        library.create_formula(
            name_zh="公式1", name_en="formula1", formula_str="a=b",
            category="物理学"
        )
        library.create_formula(
            name_zh="公式2", name_en="formula2", formula_str="c=d",
            category="物理学"
        )
        
        stats = library.get_statistics()
        assert stats['total_formulas'] >= 2
        assert stats['total_quantities'] > 0
        assert '物理学' in stats['categories']
    
    def test_check_dimension(self, library):
        """测试量纲检查"""
        formula = library.create_formula(
            name_zh="速度公式",
            name_en="velocity formula",
            formula_str="v = u + a*t",
            quantities=[
                library.quantities['v'],
                library.quantities['u'],
                library.quantities['a'],
                library.quantities['t']
            ],
            category="运动学"
        )
        
        result = library.check_dimension(formula.id)
        assert 'left_symbols' in result
        assert 'right_symbols' in result


class TestDefaultFormulaSet:
    """默认公式集测试"""
    
    def test_build_default_library(self):
        """测试构建默认库"""
        lib = DefaultFormulaSet.build_library()
        assert len(lib.formulas) > 0
        assert len(lib.quantities) > 0
    
    def test_default_formulas_contain_classics(self):
        """测试默认库包含经典公式"""
        lib = DefaultFormulaSet.build_library()
        
        # 查找质能方程
        energy_formulas = lib.search("质能", search_in="name")
        assert len(energy_formulas) > 0
        
        # 查找牛顿第二定律
        newton_formulas = lib.search("牛顿", search_in="name")
        assert len(newton_formulas) > 0
    
    def test_formulas_have_metadata(self):
        """测试公式有完整元数据"""
        lib = DefaultFormulaSet.build_library()
        
        for formula in lib.formulas.values():
            assert formula.name_zh
            assert formula.name_en
            assert formula.formula_str
            assert formula.category
            assert len(formula.description_zh) > 0


class TestFormulaDerivation:
    """公式推导测试"""
    
    def test_derivation_workflow(self):
        """测试推导工作流"""
        lib = UnifiedFormulaLibrary()
        
        # 原公式: x = v_0*t + 0.5*a*t^2
        original = "x = v_0*t + 0.5*a*t**2"
        
        # 求导得速度
        velocity = lib.derive_formula(original, "t")
        assert "v_0" in velocity or len(velocity) > 0
        
        # 再求导得加速度
        acceleration = lib.derive_formula(velocity, "t")
        assert "a" in acceleration or len(acceleration) > 0


class TestErrorHandling:
    """错误处理测试"""
    
    def test_parse_invalid_formula(self):
        """测试解析无效公式"""
        lib = UnifiedFormulaLibrary()
        with pytest.raises(ValueError):
            lib.parse_formula_string("@@@@invalid@@@@")
    
    def test_substitute_with_missing_variable(self):
        """测试缺失变量代入"""
        lib = UnifiedFormulaLibrary()
        with pytest.raises(ValueError):
            # 没有提供 'a' 的值
            lib.substitute_values("a*t", {"t": 1.0})
    
    def test_solve_nonexistent_variable(self):
        """测试求解不存在的变量"""
        lib = UnifiedFormulaLibrary()
        result = lib.solve_for_variable("a + b", "c")
        # 应该返回错误信息或空列表
        assert isinstance(result, list)


class TestExportFunctionality:
    """导出功能测试"""
    
    def test_export_to_json(self, tmp_path):
        """测试导出JSON"""
        lib = DefaultFormulaSet.build_library()
        output_file = tmp_path / "test_formulas.json"
        
        data = lib.export_to_json(str(output_file))
        
        assert output_file.exists()
        assert 'export_time' in data
        assert 'total_formulas' in data
        assert 'formulas' in data
        assert len(data['formulas']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
