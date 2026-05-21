"""
SQLAlchemy ORM 数据库模型
完整的数据持久化层，支持关系映射和高级查询
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, JSON, Boolean,
    ForeignKey, Table, Index, UniqueConstraint, CheckConstraint,
    create_engine, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID
import uuid
import json

Base = declarative_base()

# 关联表：公式与物理量的多对多关系
formula_quantity = Table(
    'formula_quantity',
    Base.metadata,
    Column('formula_id', String(50), ForeignKey('formulas.id', ondelete='CASCADE')),
    Column('quantity_symbol', String(10), ForeignKey('quantities.symbol', ondelete='CASCADE')),
    Index('idx_formula_quantity', 'formula_id', 'quantity_symbol')
)


class FormulaDB(Base):
    """物理公式数据库模型"""
    __tablename__ = 'formulas'
    
    # 主键和基本字段
    id = Column(String(50), primary_key=True, default=lambda: f"fm_{uuid.uuid4().hex[:12]}")
    name_zh = Column(String(255), nullable=False, unique=True, index=True)
    name_en = Column(String(255), index=True)
    
    # 公式表示
    formula_str = Column(String(1000), nullable=False)  # E = m*c**2
    latex_str = Column(String(1000))  # E = mc^{2}
    formula_hash = Column(String(32), unique=True, index=True)  # 去重用
    
    # 描述
    description_zh = Column(String(1000))
    description_en = Column(String(1000))
    
    # 分类
    category = Column(String(50), nullable=False, index=True)  # 力学、热学等
    subcategory = Column(String(50), index=True)  # 运动学、动力学等
    
    # 应用和关系
    applications = Column(JSON, default=list)  # ["核反应", "粒子物理"]
    prerequisites = Column(JSON, default=list)  # 前置公式 IDs
    
    # 版本和元数据
    version = Column(String(20), default='1.0')
    notes = Column(String(1000))
    is_validated = Column(Boolean, default=False)  # 量纲是否已验证
    validation_status = Column(String(50))  # PASS, FAIL, UNKNOWN
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # 关系
    quantities = relationship(
        'QuantityDB',
        secondary=formula_quantity,
        backref='formulas',
        cascade='save-update, merge'
    )
    derivations = relationship(
        'DerivationDB',
        back_populates='formula',
        cascade='all, delete-orphan'
    )
    dimension_checks = relationship(
        'DimensionCheckDB',
        back_populates='formula',
        cascade='all, delete-orphan'
    )
    
    __table_args__ = (
        UniqueConstraint('name_zh', 'version', name='uq_formula_version'),
        Index('idx_formula_category_time', 'category', 'created_at'),
        Index('idx_formula_search', 'name_zh', 'description_zh'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'formula': self.formula_str,
            'latex': self.latex_str,
            'description_zh': self.description_zh,
            'category': self.category,
            'applications': self.applications,
            'is_validated': self.is_validated,
            'validation_status': self.validation_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'quantities': [q.symbol for q in self.quantities]
        }
    
    @hybrid_property
    def symbol_count(self) -> int:
        """涉及的物理量数量"""
        return len(self.quantities)
    
    @hybrid_property
    def is_recent(self) -> bool:
        """是否为最近创建（7天内）"""
        from datetime import timedelta
        return (datetime.utcnow() - self.created_at) < timedelta(days=7)


class QuantityDB(Base):
    """物理量数据库模型"""
    __tablename__ = 'quantities'
    
    # 主键
    symbol = Column(String(10), primary_key=True)  # v, m, E等
    
    # 基本信息
    name_zh = Column(String(255), nullable=False, index=True)
    name_en = Column(String(255), index=True)
    description = Column(String(500))
    
    # 量纲
    dimension = Column(String(50), nullable=False, index=True)  # MLT⁻²
    dimension_components = Column(JSON)  # {"M": 1, "L": 1, "T": -2}
    
    # 单位
    unit = Column(String(50), nullable=False)  # kg, m/s等
    si_unit = Column(String(50))  # 标准SI单位
    
    # 分类
    category = Column(String(50), index=True)  # 基本量、导出量等
    is_constant = Column(Boolean, default=False, index=True)
    
    # 典型范围
    typical_range_min = Column(Float)
    typical_range_max = Column(Float)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    is_standard = Column(Boolean, default=True)  # 是否为标准量
    
    __table_args__ = (
        Index('idx_quantity_search', 'name_zh', 'name_en'),
        Index('idx_quantity_dimension', 'dimension'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'dimension': self.dimension,
            'unit': self.unit,
            'category': self.category,
            'is_constant': self.is_constant,
            'typical_range': [self.typical_range_min, self.typical_range_max]
        }


class DerivationDB(Base):
    """公式推导记录数据库模型"""
    __tablename__ = 'derivations'
    
    # 主键
    id = Column(String(50), primary_key=True, default=lambda: f"dv_{uuid.uuid4().hex[:12]}")
    
    # 关系
    formula_id = Column(String(50), ForeignKey('formulas.id', ondelete='CASCADE'), index=True)
    formula = relationship('FormulaDB', back_populates='derivations')
    
    # 推导信息
    source_formula_str = Column(String(1000), nullable=False)
    operation = Column(String(50), nullable=False, index=True)  # 求导、积分、变形
    operation_details = Column(JSON)  # {"type": "derivative", "variable": "t", "order": 1}
    
    # 结果
    result_formula_str = Column(String(1000), nullable=False)
    result_latex = Column(String(1000))
    
    # 推导步骤
    steps = Column(JSON, default=list)  # 分步骤的推导过程
    difficulty_level = Column(String(20))  # easy, medium, hard
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_derivation_formula_op', 'formula_id', 'operation'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'formula_id': self.formula_id,
            'operation': self.operation,
            'source': self.source_formula_str,
            'result': self.result_formula_str,
            'steps': self.steps,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DimensionCheckDB(Base):
    """量纲验证记录数据库模型"""
    __tablename__ = 'dimension_checks'
    
    # 主键
    id = Column(String(50), primary_key=True, default=lambda: f"dc_{uuid.uuid4().hex[:12]}")
    
    # 关系
    formula_id = Column(String(50), ForeignKey('formulas.id', ondelete='CASCADE'), index=True)
    formula = relationship('FormulaDB', back_populates='dimension_checks')
    
    # 检查信息
    left_side_expr = Column(String(500))  # E
    right_side_expr = Column(String(500))  # m*c**2
    
    # 量纲分析
    left_dimension = Column(String(100))  # ML²T⁻²
    right_dimension = Column(String(100))  # ML²T⁻²
    left_dim_components = Column(JSON)  # {"M": 1, "L": 2, "T": -2}
    right_dim_components = Column(JSON)
    
    # 验证结果
    is_consistent = Column(Boolean, nullable=False, index=True)
    match_percentage = Column(Float)  # 0-100
    error_message = Column(String(500))
    
    # 符号分析
    all_symbols = Column(JSON)  # 所有出现的符号
    undefined_symbols = Column(JSON, default=list)  # 未定义的符号
    
    # 时间戳
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_dimension_check_consistency', 'is_consistent'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'formula_id': self.formula_id,
            'is_consistent': self.is_consistent,
            'match_percentage': self.match_percentage,
            'left_dimension': self.left_dimension,
            'right_dimension': self.right_dimension,
            'undefined_symbols': self.undefined_symbols,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None
        }


class FormulaSearchDB(Base):
    """公式搜索索引表（提升搜索性能）"""
    __tablename__ = 'formula_search_index'
    
    # 主键
    id = Column(String(50), primary_key=True)
    formula_id = Column(String(50), ForeignKey('formulas.id', ondelete='CASCADE'), index=True)
    
    # 搜索字段（规范化）
    name_zh_lower = Column(String(255), index=True)
    name_en_lower = Column(String(255), index=True)
    description_zh_lower = Column(String(1000), index=True)
    category_lower = Column(String(50), index=True)
    
    # 搜索权重
    relevance_score = Column(Float, default=0.0, index=True)
    search_count = Column(Integer, default=0)  # 被搜索的次数
    
    # 时间戳
    indexed_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_search_full_text', 'name_zh_lower', 'description_zh_lower'),
    )


class DatabaseQueryHelper:
    """数据库查询助手类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_formula_by_id(self, formula_id: str) -> Optional[FormulaDB]:
        """根据ID获取公式"""
        return self.session.query(FormulaDB).filter(
            FormulaDB.id == formula_id
        ).first()
    
    def get_formulas_by_category(self, category: str, limit: int = 50) -> List[FormulaDB]:
        """按分类获取公式"""
        return self.session.query(FormulaDB).filter(
            FormulaDB.category == category
        ).order_by(FormulaDB.created_at.desc()).limit(limit).all()
    
    def search_formulas(
        self,
        keyword: str,
        search_type: str = 'all',
        limit: int = 50
    ) -> List[FormulaDB]:
        """全文搜索公式"""
        keyword_lower = keyword.lower()
        query = self.session.query(FormulaDB)
        
        if search_type in ['all', 'name']:
            query = query.filter(
                (FormulaDB.name_zh.ilike(f'%{keyword}%')) |
                (FormulaDB.name_en.ilike(f'%{keyword}%'))
            )
        elif search_type == 'description':
            query = query.filter(
                (FormulaDB.description_zh.ilike(f'%{keyword}%')) |
                (FormulaDB.description_en.ilike(f'%{keyword}%'))
            )
        elif search_type == 'category':
            query = query.filter(FormulaDB.category.ilike(f'%{keyword}%'))
        
        return query.order_by(FormulaDB.created_at.desc()).limit(limit).all()
    
    def get_formulas_by_quantity(self, symbol: str, limit: int = 50) -> List[FormulaDB]:
        """获取包含特定物理量的公式"""
        return self.session.query(FormulaDB).join(
            formula_quantity
        ).filter(
            formula_quantity.c.quantity_symbol == symbol
        ).limit(limit).all()
    
    def get_validated_formulas(self, limit: int = 100) -> List[FormulaDB]:
        """获取已验证的公式"""
        return self.session.query(FormulaDB).filter(
            FormulaDB.is_validated == True,
            FormulaDB.validation_status == 'PASS'
        ).order_by(FormulaDB.created_at.desc()).limit(limit).all()
    
    def get_recent_formulas(self, days: int = 7, limit: int = 50) -> List[FormulaDB]:
        """获取最近添加的公式"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.session.query(FormulaDB).filter(
            FormulaDB.created_at >= cutoff_date
        ).order_by(FormulaDB.created_at.desc()).limit(limit).all()
    
    def get_formulas_by_dimension(self, dimension: str, limit: int = 50) -> List[FormulaDB]:
        """根据量纲获取公式"""
        return self.session.query(FormulaDB).join(
            formula_quantity
        ).join(
            QuantityDB,
            formula_quantity.c.quantity_symbol == QuantityDB.symbol
        ).filter(
            QuantityDB.dimension == dimension
        ).distinct().limit(limit).all()
    
    def get_formula_with_derivations(self, formula_id: str) -> Optional[FormulaDB]:
        """获取包含所有推导的公式"""
        return self.session.query(FormulaDB).options(
            # 一次性加载所有关联数据（避免N+1查询问题）
            
        ).filter(
            FormulaDB.id == formula_id
        ).first()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        total_formulas = self.session.query(FormulaDB).count()
        total_quantities = self.session.query(QuantityDB).count()
        
        # 按分类统计
        categories = self.session.query(
            FormulaDB.category,
            func.count(FormulaDB.id).label('count')
        ).group_by(FormulaDB.category).all()
        
        # 验证统计
        validated = self.session.query(FormulaDB).filter(
            FormulaDB.is_validated == True
        ).count()
        
        return {
            'total_formulas': total_formulas,
            'total_quantities': total_quantities,
            'validated_count': validated,
            'validation_rate': (validated / total_formulas * 100) if total_formulas > 0 else 0,
            'categories': {cat: count for cat, count in categories},
            'recent_formulas': self.session.query(FormulaDB).order_by(
                FormulaDB.created_at.desc()
            ).limit(5).count()
        }


# 导入func用于统计查询
from sqlalchemy import func
