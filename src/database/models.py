"""
数据库 ORM 模型 - SQLAlchemy
完整的数据库模式设计
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, 
    ForeignKey, JSON, Boolean, Text, Table, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from datetime import datetime
from typing import Optional, List

Base = declarative_base()


# 关联表 - 公式与物理量的多对多关系
formula_quantity_association = Table(
    'formula_quantity_association',
    Base.metadata,
    Column('formula_id', String(50), ForeignKey('formulas.id'), primary_key=True),
    Column('quantity_id', String(50), ForeignKey('quantities.id'), primary_key=True)
)


class FormulaDB(Base):
    """物理公式表
    
    存储所有物理公式及其元数据
    """
    __tablename__ = 'formulas'
    
    # 基本信息
    id = Column(String(50), primary_key=True, index=True)
    name_zh = Column(String(255), nullable=False, unique=True, index=True)
    name_en = Column(String(255), index=True)
    
    # 公式表示
    formula_str = Column(String(1000), nullable=False)
    latex_str = Column(String(1000))
    
    # 分类与描述
    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(50), index=True)
    description_zh = Column(Text)
    description_en = Column(Text)
    
    # 关系数据
    applications = Column(JSON, default=[])  # 应用领域列表
    prerequisites = Column(JSON, default=[])  # 前置公式列表
    notes = Column(Text)
    
    # 版本与时间戳
    version = Column(String(20), default='1.0')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    quantities = relationship(
        "QuantityDB",
        secondary=formula_quantity_association,
        back_populates="formulas"
    )
    derivations = relationship("DerivationDB", back_populates="formula", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_formula_category_created', 'category', 'created_at'),
        Index('idx_formula_name_zh', 'name_zh'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'formula_str': self.formula_str,
            'latex_str': self.latex_str,
            'category': self.category,
            'subcategory': self.subcategory,
            'description_zh': self.description_zh,
            'description_en': self.description_en,
            'applications': self.applications,
            'prerequisites': self.prerequisites,
            'notes': self.notes,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'quantities': [q.to_dict() for q in self.quantities]
        }


class QuantityDB(Base):
    """物理量表
    
    存储所有物理量的定义
    """
    __tablename__ = 'quantities'
    
    # 基本信息
    id = Column(String(50), primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name_zh = Column(String(255), nullable=False, index=True)
    name_en = Column(String(255))
    
    # 物理属性
    dimension = Column(String(50), nullable=False, index=True)
    unit = Column(String(50), nullable=False)
    description = Column(Text)
    
    # 分类
    category = Column(String(50), default='基本量', index=True)
    
    # 特性
    is_constant = Column(Boolean, default=False, index=True)
    typical_range_min = Column(Float, nullable=True)
    typical_range_max = Column(Float, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    formulas = relationship(
        "FormulaDB",
        secondary=formula_quantity_association,
        back_populates="quantities"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_quantity_symbol', 'symbol'),
        Index('idx_quantity_dimension', 'dimension'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name_zh': self.name_zh,
            'name_en': self.name_en,
            'dimension': self.dimension,
            'unit': self.unit,
            'description': self.description,
            'category': self.category,
            'is_constant': self.is_constant,
            'typical_range': [self.typical_range_min, self.typical_range_max]
            if self.typical_range_min is not None else None
        }


class DerivationDB(Base):
    """公式推导记录表
    
    记录从一个公式推导到另一个公式的过程
    """
    __tablename__ = 'derivations'
    
    # 基本信息
    id = Column(String(50), primary_key=True, index=True)
    formula_id = Column(String(50), ForeignKey('formulas.id'), nullable=False, index=True)
    
    # 推导信息
    operation = Column(String(50), nullable=False, index=True)  # 求导/积分/变形等
    result_formula = Column(String(1000), nullable=False)
    
    # 详细步骤
    steps = Column(JSON, default=[])
    description = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 关系
    formula = relationship("FormulaDB", back_populates="derivations")
    
    # 索引
    __table_args__ = (
        Index('idx_derivation_formula_operation', 'formula_id', 'operation'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'formula_id': self.formula_id,
            'operation': self.operation,
            'result_formula': self.result_formula,
            'steps': self.steps,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }


class DimensionCheckDB(Base):
    """量纲检查记录表
    
    记录公式的量纲一致性检查结果
    """
    __tablename__ = 'dimension_checks'
    
    # 基本信息
    id = Column(String(50), primary_key=True, index=True)
    formula_id = Column(String(50), ForeignKey('formulas.id'), nullable=False, index=True)
    
    # 检查结果
    is_consistent = Column(Boolean, nullable=False, index=True)
    left_dimension = Column(String(100))
    right_dimension = Column(String(100))
    match_percentage = Column(Float)
    
    # 详细信息
    details = Column(JSON)
    
    # 时间戳
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 索引
    __table_args__ = (
        Index('idx_dimension_check_formula', 'formula_id', 'checked_at'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'formula_id': self.formula_id,
            'is_consistent': self.is_consistent,
            'left_dimension': self.left_dimension,
            'right_dimension': self.right_dimension,
            'match_percentage': self.match_percentage,
            'details': self.details,
            'checked_at': self.checked_at.isoformat()
        }


class FormulaSearchDB(Base):
    """公式搜索索引表（可选，用于全文搜索优化）
    
    存储公式的可搜索字段组合
    """
    __tablename__ = 'formula_search_index'
    
    # 基本信息
    id = Column(String(50), primary_key=True, ForeignKey('formulas.id'))
    formula_id = Column(String(50), nullable=False)
    
    # 搜索内容 (合并所有可搜索字段)
    search_text = Column(Text, nullable=False)
    
    # 搜索权重
    name_weight = Column(Float, default=2.0)
    category_weight = Column(Float, default=1.5)
    description_weight = Column(Float, default=1.0)
    
    # 更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_search_text', 'search_text'),
    )


# ===================== 数据库会话管理 =====================

class DatabaseSession:
    """数据库会话管理器"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            echo=False,  # 设置为 True 以输出 SQL 语句
            pool_pre_ping=True,  # 检查连接是否有效
            pool_size=20,
            max_overflow=40
        )
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        print("✅ 数据库表创建完成")
    
    def drop_tables(self):
        """删除所有表（谨慎使用）"""
        Base.metadata.drop_all(self.engine)
        print("⚠️  所有表已删除")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=self.engine)
        return SessionLocal()
    
    def init_sample_data(self):
        """初始化示例数据"""
        session = self.get_session()
        try:
            # 创建示例物理量
            quantities = [
                QuantityDB(
                    id='qty_001',
                    symbol='v',
                    name_zh='速度',
                    name_en='velocity',
                    dimension='LT⁻¹',
                    unit='m/s',
                    category='运动学'
                ),
                QuantityDB(
                    id='qty_002',
                    symbol='m',
                    name_zh='质量',
                    name_en='mass',
                    dimension='M',
                    unit='kg',
                    category='基本量'
                ),
                QuantityDB(
                    id='qty_003',
                    symbol='E',
                    name_zh='能量',
                    name_en='energy',
                    dimension='ML²T⁻²',
                    unit='J',
                    category='能量'
                ),
                QuantityDB(
                    id='qty_004',
                    symbol='c',
                    name_zh='光速',
                    name_en='light speed',
                    dimension='LT⁻¹',
                    unit='m/s',
                    category='常数',
                    is_constant=True
                ),
            ]
            session.add_all(quantities)
            
            # 创建示例公式
            formula = FormulaDB(
                id='fm_001',
                name_zh='质能方程',
                name_en='Mass-energy equivalence',
                formula_str='E = m*c**2',
                latex_str='E = mc^{2}',
                category='相对论',
                description_zh='质量与能量的相互转换关系',
                description_en='The conversion between mass and energy',
                applications=['核反应', '粒子物理'],
                notes='爱因斯坦著名公式'
            )
            session.add(formula)
            
            session.commit()
            print("✅ 示例数据初始化完成")
        except Exception as e:
            session.rollback()
            print(f"❌ 初始化失败: {e}")
        finally:
            session.close()


# ===================== 数据库查询助手 =====================

class FormulaQueryHelper:
    """公式查询助手"""
    
    @staticmethod
    def get_formula_by_id(session: Session, formula_id: str) -> Optional[FormulaDB]:
        """按ID获取公式"""
        return session.query(FormulaDB).filter(FormulaDB.id == formula_id).first()
    
    @staticmethod
    def get_formulas_by_category(session: Session, category: str) -> List[FormulaDB]:
        """按分类获取公式"""
        return session.query(FormulaDB).filter(FormulaDB.category == category).all()
    
    @staticmethod
    def search_formulas(session: Session, keyword: str) -> List[FormulaDB]:
        """搜索公式"""
        keyword = f"%{keyword}%"
        return session.query(FormulaDB).filter(
            (FormulaDB.name_zh.ilike(keyword)) |
            (FormulaDB.name_en.ilike(keyword)) |
            (FormulaDB.description_zh.ilike(keyword))
        ).all()
    
    @staticmethod
    def get_quantity_by_symbol(session: Session, symbol: str) -> Optional[QuantityDB]:
        """按符号获取物理量"""
        return session.query(QuantityDB).filter(QuantityDB.symbol == symbol).first()
    
    @staticmethod
    def get_all_quantities(session: Session) -> List[QuantityDB]:
        """获取所有物理量"""
        return session.query(QuantityDB).all()
    
    @staticmethod
    def get_derivations(session: Session, formula_id: str) -> List[DerivationDB]:
        """获取公式的推导记录"""
        return session.query(DerivationDB).filter(
            DerivationDB.formula_id == formula_id
        ).all()


if __name__ == "__main__":
    # 示例：初始化数据库
    db = DatabaseSession("sqlite:///formula_system.db")
    db.create_tables()
    db.init_sample_data()
    
    # 示例：查询数据
    session = db.get_session()
    formula = FormulaQueryHelper.get_formula_by_id(session, 'fm_001')
    if formula:
        print(f"\n找到公式: {formula.name_zh}")
        print(f"公式: {formula.formula_str}")
        print(f"LaTeX: {formula.latex_str}")
    
    session.close()
