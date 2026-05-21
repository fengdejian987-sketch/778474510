"""
公式业务逻辑层 - 处理复杂的业务逻辑和数据处理
提供高级API接口，隐藏数据库细节
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.unified_library import (
    UnifiedFormulaLibrary,
    PhysicalFormula,
    PhysicalQuantity,
    DimensionAnalyzer,
    DimensionType
)
from src.database.models import (
    FormulaDB, QuantityDB, DerivationDB, DimensionCheckDB, DatabaseQueryHelper
)


class FormulaService:
    """公式服务 - 处理公式的创建、查询、修改、删除等操作"""
    
    def __init__(self, session: Session):
        self.session = session
        self.lib = UnifiedFormulaLibrary()
        self.query_helper = DatabaseQueryHelper(session)
        self._cache = {}  # 简单的内存缓存
    
    def create_formula(
        self,
        name_zh: str,
        name_en: str,
        formula_str: str,
        category: str,
        description_zh: str = "",
        description_en: str = "",
        latex_str: str = "",
        applications: List[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """创建新公式
        
        Args:
            name_zh: 中文名称
            name_en: 英文名称
            formula_str: 公式字符串 (e.g., "E = m*c**2")
            category: 分类 (e.g., "相对论")
            description_zh: 中文描述
            description_en: 英文描述
            latex_str: LaTeX 格式
            applications: 应用领域
            notes: 备注
        
        Returns:
            创建的公式信息字典
        """
        try:
            # 1. 生成哈希值（用于去重）
            formula_hash = self._generate_formula_hash(name_zh, formula_str)
            
            # 2. 检查是否已存在
            existing = self.session.query(FormulaDB).filter(
                FormulaDB.formula_hash == formula_hash
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'error': f'该公式已存在: {existing.id}',
                    'existing_id': existing.id
                }
            
            # 3. 验证公式格式
            validation = self._validate_formula_format(formula_str)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f'公式格式错误: {validation["error"]}'
                }
            
            # 4. 生成 LaTeX
            if not latex_str:
                latex_str = self.lib.parse_to_latex(formula_str)
            
            # 5. 创建数据库记录
            formula_db = FormulaDB(
                name_zh=name_zh,
                name_en=name_en,
                formula_str=formula_str,
                formula_hash=formula_hash,
                latex_str=latex_str,
                description_zh=description_zh,
                description_en=description_en,
                category=category,
                applications=applications or [],
                notes=notes,
                is_validated=False
            )
            
            # 6. 添加物理量关系
            quantities = self._extract_quantities(formula_str)
            for qty_symbol in quantities:
                qty = self.session.query(QuantityDB).filter(
                    QuantityDB.symbol == qty_symbol
                ).first()
                if qty:
                    formula_db.quantities.append(qty)
            
            # 7. 保存到数据库
            self.session.add(formula_db)
            self.session.commit()
            
            # 8. 清除缓存
            self._clear_cache()
            
            return {
                'success': True,
                'id': formula_db.id,
                'message': f'公式 {name_zh} 创建成功',
                'formula': formula_db.to_dict()
            }
        
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_formula(self, formula_id: str) -> Optional[Dict[str, Any]]:
        """获取公式详情"""
        # 检查缓存
        if formula_id in self._cache:
            return self._cache[formula_id]
        
        formula = self.query_helper.get_formula_by_id(formula_id)
        
        if not formula:
            return None
        
        result = formula.to_dict()
        
        # 添加推导信息
        derivations = self.session.query(DerivationDB).filter(
            DerivationDB.formula_id == formula_id
        ).all()
        result['derivations'] = [d.to_dict() for d in derivations]
        
        # 添加量纲检查信息
        dim_check = self.session.query(DimensionCheckDB).filter(
            DimensionCheckDB.formula_id == formula_id
        ).order_by(DimensionCheckDB.checked_at.desc()).first()
        
        if dim_check:
            result['dimension_check'] = dim_check.to_dict()
        
        # 缓存结果
        self._cache[formula_id] = result
        
        return result
    
    def search_formulas(
        self,
        keyword: str,
        search_type: str = 'all',
        category: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """搜索公式
        
        Args:
            keyword: 搜索关键字
            search_type: 搜索类型 (all, name, description, category)
            category: 可选的分类过滤
            limit: 结果数量限制
        
        Returns:
            搜索结果
        """
        try:
            # 使用查询助手进行搜索
            results = self.query_helper.search_formulas(
                keyword=keyword,
                search_type=search_type,
                limit=limit
            )
            
            # 过滤分类（如果指定）
            if category:
                results = [f for f in results if f.category == category]
            
            return {
                'success': True,
                'count': len(results),
                'keyword': keyword,
                'results': [f.to_dict() for f in results]
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_formula_dimension(self, formula_id: str) -> Dict[str, Any]:
        """验证公式的量纲一致性
        
        Args:
            formula_id: 公式ID
        
        Returns:
            验证结果
        """
        try:
            formula = self.query_helper.get_formula_by_id(formula_id)
            
            if not formula:
                return {'success': False, 'error': '公式不存在'}
            
            # 使用库的验证方法
            validation = DimensionAnalyzer.check_consistency(
                PhysicalFormula(
                    id=formula.id,
                    name_zh=formula.name_zh,
                    name_en=formula.name_en,
                    formula_str=formula.formula_str,
                    latex_str=formula.latex_str
                )
            )
            
            # 保存验证结果到数据库
            dim_check = DimensionCheckDB(
                formula_id=formula_id,
                left_side_expr=formula.formula_str.split('=')[0].strip() if '=' in formula.formula_str else '',
                right_side_expr=formula.formula_str.split('=')[1].strip() if '=' in formula.formula_str else '',
                is_consistent=validation.get('is_consistent', False),
                all_symbols=list(validation.get('left_symbols', []) | validation.get('right_symbols', [])),
                undefined_symbols=validation.get('undefined_symbols', [])
            )
            
            self.session.add(dim_check)
            
            # 更新公式的验证状态
            formula.is_validated = True
            formula.validation_status = 'PASS' if validation.get('is_consistent') else 'FAIL'
            
            self.session.commit()
            
            return {
                'success': True,
                'formula_id': formula_id,
                'is_consistent': validation.get('is_consistent'),
                'details': validation
            }
        
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def derive_formula(
        self,
        formula_id: str,
        operation: str,
        **kwargs
    ) -> Dict[str, Any]:
        """推导公式
        
        Args:
            formula_id: 公式ID
            operation: 操作类型 (derivative, integrate, transform)
            **kwargs: 操作参数
                - variable: 求导/积分的变量
                - order: 求导阶数
        
        Returns:
            推导结果
        """
        try:
            formula = self.query_helper.get_formula_by_id(formula_id)
            
            if not formula:
                return {'success': False, 'error': '公式不存在'}
            
            result_formula_str = None
            steps = []
            
            # 执行操作
            if operation == 'derivative':
                variable = kwargs.get('variable')
                order = kwargs.get('order', 1)
                
                result_formula_str = self.lib.derive_formula(
                    formula.formula_str,
                    variable,
                    order
                )
                steps.append(f"对 {variable} 求 {order} 阶导数")
            
            elif operation == 'integrate':
                variable = kwargs.get('variable')
                result_formula_str = self.lib.integrate_formula(
                    formula.formula_str,
                    variable
                )
                steps.append(f"对 {variable} 积分")
            
            elif operation == 'solve':
                variable = kwargs.get('variable')
                solutions = self.lib.solve_for_variable(
                    formula.formula_str,
                    variable
                )
                result_formula_str = f"[{', '.join(solutions)}]"
                steps.append(f"解出 {variable}")
            
            # 保存推导记录
            derivation = DerivationDB(
                formula_id=formula_id,
                source_formula_str=formula.formula_str,
                operation=operation,
                operation_details=kwargs,
                result_formula_str=result_formula_str,
                result_latex=self.lib.parse_to_latex(result_formula_str) if result_formula_str else '',
                steps=steps
            )
            
            self.session.add(derivation)
            self.session.commit()
            
            # 清除缓存
            self._clear_cache(formula_id)
            
            return {
                'success': True,
                'derivation_id': derivation.id,
                'operation': operation,
                'source': formula.formula_str,
                'result': result_formula_str,
                'steps': steps
            }
        
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.query_helper.get_statistics()
    
    def get_formulas_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类获取公式"""
        formulas = self.query_helper.get_formulas_by_category(category)
        return [f.to_dict() for f in formulas]
    
    def get_recent_formulas(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取最近添加的公式"""
        formulas = self.query_helper.get_recent_formulas(days)
        return [f.to_dict() for f in formulas]
    
    # 私有方法
    
    def _generate_formula_hash(self, name_zh: str, formula_str: str) -> str:
        """生成公式哈希值用于去重"""
        content = f"{name_zh}_{formula_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _validate_formula_format(self, formula_str: str) -> Dict[str, Any]:
        """验证公式格式"""
        if not formula_str:
            return {'valid': False, 'error': '公式不能为空'}
        
        if '=' not in formula_str:
            return {'valid': False, 'error': '公式必须包含等号'}
        
        try:
            self.lib.parse_formula_string(formula_str)
            return {'valid': True}
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _extract_quantities(self, formula_str: str) -> List[str]:
        """从公式字符串中提取物理量符号"""
        import re
        # 匹配所有单个字母或希腊字母
        symbols = set()
        for match in re.finditer(r'[a-zA-Z_]\w*', formula_str):
            symbol = match.group()
            # 排除数字和常见函数名
            if symbol not in ['sin', 'cos', 'tan', 'sqrt', 'exp', 'log', 'e', 'pi']:
                symbols.add(symbol[0])  # 取第一个字符作为符号
        
        return list(symbols)
    
    def _clear_cache(self, formula_id: str = None):
        """清除缓存"""
        if formula_id:
            self._cache.pop(formula_id, None)
        else:
            self._cache.clear()
