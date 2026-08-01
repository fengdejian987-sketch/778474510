from sqlalchemy import create_engine, Column, String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class FormulaDB(Base):
    __tablename__ = 'formulas'
    id = Column(String(50), primary_key=True)
    name_zh = Column(String(255), nullable=False, unique=True)
    name_en = Column(String(255))
    formula_str = Column(String(1000), nullable=False)
    latex_str = Column(String(1000))
    category = Column(String(50), index=True)
    description_zh = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)
    version = Column(String(20))
    derivations = relationship("DerivationDB", back_populates="formula")

class QuantityDB(Base):
    __tablename__ = 'quantities'
    id = Column(String(50), primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    name_zh = Column(String(255))
    dimension = Column(String(50))
    unit = Column(String(50))

class DerivationDB(Base):
    __tablename__ = 'derivations'
    id = Column(String(50), primary_key=True)
    formula_id = Column(String(50), ForeignKey('formulas.id'))
    operation = Column(String(50))
    result_formula = Column(String(1000))
    steps = Column(JSON)
    formula = relationship("FormulaDB", back_populates="derivations")
