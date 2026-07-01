#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冯德建公式系统 - 公式服务
核心业务逻辑实现

Author: Service Layer v3.0
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from src.core.unified_formula_library import (
    UnifiedFormulaLibrary,
    PhysicalFormula,
    PhysicalQuantity,
    DimensionType,
    FormulaDerivation,
    DefaultFormulaSet,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class FormulaSearchResult:
    """公式搜索结果"""
    formula_id: str
    name_zh: str
    name_en: str
    formula_str: str
    latex_str: str
    category: str
    match_score: float = 1.0


@dataclass
class CalculationResult:
    """计算结果"""
    success: bool
    result: Any
    formula_id: Optional[str] = None
    description: str = ""
    timestamp: str = ""
    error: Optional[str] = None


class FormulaService:
    """公式服务层 - 核心业务逻辑"""
    
    def __init__(self, library: Optional[UnifiedFormulaLibrary] = None):
        """初始化服务"""
        self.library = library or DefaultFormulaSet.build_library()
        self._cache = {}
        logger.info("✓ 公式服务已初始化")
    
    def add_formula(self, name_zh: str, name_en: str, formula_str: str,
                   description_zh: str = "", description_en: str = "",
                   category: str = "通用", **kwargs) -> PhysicalFormula:
        """添加新公式"""
        try:
            formula = self.library.create_formula(
                name_zh=name_zh,
                name_en=name_en,
                formula_str=formula_str,
                description_zh=description_zh,
                description_en=description_en,
                category=category,
                **kwargs
            )
            self._invalidate_cache()
            logger.info(f"✓ 公式已添加: {formula.id} - {name_zh}")
            return formula
        except Exception as e:
            logger.error(f"✗ 添加公式失败: {e}")
            raise
    
    def get_formula(self, formula_id: str) -> Optional[PhysicalFormula]:
        """获取公式"""
        return self.library.formulas.get(formula_id)
    
    def list_formulas(self, category: Optional[str] = None) -> List[PhysicalFormula]:
        """列出公式"""
        formulas = list(self.library.formulas.values())
        if category:
            formulas = [f for f in formulas if f.category == category]
        return formulas
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = set()
        for formula in self.library.formulas.values():
            if formula.category:
                categories.add(formula.category)
        return sorted(list(categories))
    
    def search_formulas(self, keyword: str, search_type: str = 'all',
                       category: Optional[str] = None) -> List[FormulaSearchResult]:
        """搜索公式"""
        results = []
        formulas = self.library.search(keyword, search_in=search_type)
        
        if category:
            formulas = [f for f in formulas if f.category == category]
        
        for formula in formulas:
            result = FormulaSearchResult(
                formula_id=formula.id,
                name_zh=formula.name_zh,
                name_en=formula.name_en,
                formula_str=formula.formula_str,
                latex_str=formula.latex_str,
                category=formula.category,
                match_score=1.0
            )
            results.append(result)
        
        return results
    
    def find_formulas_by_symbol(self, symbol: str) -> List[PhysicalFormula]:
        """根据符号查找公式"""
        matching_formulas = []
        for formula in self.library.formulas.values():
            for qty in formula.quantities:
                if qty.symbol == symbol:
                    matching_formulas.append(formula)
                    break
        return matching_formulas
    
    def calculate_derivative(self, formula_id: str, variable: str,
                            order: int = 1) -> CalculationResult:
        """计算求导"""
        try:
            formula = self.get_formula(formula_id)
            if not formula:
                return CalculationResult(
                    success=False,
                    result=None,
                    error=f"公式不存在: {formula_id}"
                )
            
            result = self.library.derive_formula(
                formula.formula_str, variable, order=order
            )
            
            return CalculationResult(
                success=True,
                result=result,
                formula_id=formula_id,
                description=f"对 {variable} 的{order}阶导数",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"求导失败: {e}")
            return CalculationResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def calculate_integral(self, formula_id: str, variable: str) -> CalculationResult:
        """计算积分"""
        try:
            formula = self.get_formula(formula_id)
            if not formula:
                return CalculationResult(
                    success=False,
                    result=None,
                    error=f"公式不存在: {formula_id}"
                )
            
            result = self.library.integrate_formula(
                formula.formula_str, variable
            )
            
            return CalculationResult(
                success=True,
                result=result,
                formula_id=formula_id,
                description=f"对 {variable} 的积分",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"积分失败: {e}")
            return CalculationResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def solve_for_variable(self, formula_id: str, target_var: str) -> CalculationResult:
        """求解变量"""
        try:
            formula = self.get_formula(formula_id)
            if not formula:
                return CalculationResult(
                    success=False,
                    result=None,
                    error=f"公式不存在: {formula_id}"
                )
            
            solutions = self.library.solve_for_variable(
                formula.formula_str, target_var
            )
            
            return CalculationResult(
                success=True,
                result=solutions,
                formula_id=formula_id,
                description=f"求解变量: {target_var}",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"求解失败: {e}")
            return CalculationResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def substitute_values(self, formula_id: str,
                         values: Dict[str, float]) -> CalculationResult:
        """代入数值"""
        try:
            formula = self.get_formula(formula_id)
            if not formula:
                return CalculationResult(
                    success=False,
                    result=None,
                    error=f"公式不存在: {formula_id}"
                )
            
            result = self.library.substitute_values(
                formula.formula_str, values
            )
            
            return CalculationResult(
                success=True,
                result=result,
                formula_id=formula_id,
                description=f"代入数值计算",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"代入失败: {e}")
            return CalculationResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    def validate_formula_dimensions(self, formula_id: str) -> Dict[str, Any]:
        """验证量纲"""
        try:
            result = self.library.check_dimension(formula_id)
            logger.info(f"✓ 量纲检查完成")
            return result
        except Exception as e:
            logger.error(f"量纲检查失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_library_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        stats = self.library.get_statistics()
        stats['formulas_by_category'] = {
            category: len(self.list_formulas(category))
            for category in self.get_categories()
        }
        stats['total_categories'] = len(self.get_categories())
        return stats
    
    def _invalidate_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def export_formulas(self, filename: str, format: str = 'json') -> bool:
        """导出公式"""
        try:
            if format == 'json':
                self.library.export_to_json(filename)
            else:
                logger.warning(f"不支持的格式: {format}")
                return False
            logger.info(f"✓ 已导出到 {filename}")
            return True
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False


class DimensionValidatorService:
    """量纲验证服务"""
    
    def __init__(self, library: UnifiedFormulaLibrary):
        """初始化"""
        self.library = library
        self.analyzer = library.dimension_analyzer
    
    def validate_formula(self, formula_str: str,
                        quantities: Optional[List[PhysicalQuantity]] = None) -> Dict[str, Any]:
        """验证公式"""
        formula = PhysicalFormula(
            id="temp",
            name_zh="临时公式",
            name_en="temporary formula",
            formula_str=formula_str,
            quantities=quantities or []
        )
        return self.analyzer.check_consistency(formula)
    
    def get_quantity_dimension(self, symbol: str) -> Optional[DimensionType]:
        """获取量纲"""
        qty = self.library.quantities.get(symbol)
        if qty:
            return qty.dimension
        return self.analyzer.get_dimension(symbol)


class FormulaDerivationService:
    """推导服务"""
    
    def __init__(self, library: UnifiedFormulaLibrary):
        """初始化"""
        self.library = library
    
    def record_derivation(self, source_formula_id: str, operation: str,
                         variable: str, result_formula: str,
                         steps: Optional[List[str]] = None) -> FormulaDerivation:
        """记录推导"""
        derivation = FormulaDerivation(
            source_formula_id=source_formula_id,
            operation=operation,
            variable=variable,
            result_formula=result_formula,
            steps=steps or []
        )
        self.library.derivations.append(derivation)
        return derivation


class CacheService:
    """缓存服务"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """初始化"""
        self._cache = {}
        self._timestamps = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """获取"""
        if key not in self._cache:
            return None
        timestamp = self._timestamps.get(key)
        if timestamp and (datetime.now().timestamp() - timestamp) > self.ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        return self._cache[key]
    
    def set(self, key: str, value: Any):
        """设置"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now().timestamp()
    
    def invalidate(self, key: Optional[str] = None):
        """清除"""
        if key:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._timestamps.clear()
