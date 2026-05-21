"""
FastAPI REST 服务 - 完整的公式管理API
整合了公式、量纲验证、ML推理的所有功能
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base, FormulaDB, QuantityDB
from src.services.formula_service import FormulaService
from src.services.dimension_validator import DeepDimensionValidator
from config.settings import settings

# 配置日志
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(settings.database.url, echo=settings.debug)
SessionLocal = sessionmaker(bind=engine)

# 创建数据库表
Base.metadata.create_all(engine)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.api.title,
    version=settings.api.version,
    description=settings.api.description,
    debug=settings.api.debug
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_credentials,
    allow_methods=settings.api.cors_methods,
    allow_headers=settings.api.cors_headers,
)

# ============ Pydantic 模型 ============

class CreateFormulaRequest(BaseModel):
    """创建公式请求"""
    name_zh: str = Field(..., min_length=1, max_length=255)
    name_en: str = Field(..., min_length=1, max_length=255)
    formula_str: str = Field(..., min_length=3, max_length=1000)
    category: str = Field(..., min_length=1, max_length=50)
    description_zh: Optional[str] = Field(None, max_length=1000)
    description_en: Optional[str] = Field(None, max_length=1000)
    latex_str: Optional[str] = Field(None, max_length=1000)
    applications: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=1000)


class DeriveFormulaRequest(BaseModel):
    """推导公式请求"""
    operation: str = Field(..., description="操作类型: derivative, integrate, solve")
    variable: Optional[str] = Field(None, description="求导/积分的变量")
    order: Optional[int] = Field(1, description="求导阶数")


class ValidateDimensionRequest(BaseModel):
    """量纲验证请求"""
    formula_str: str = Field(..., description="公式字符串")


class FormulaResponse(BaseModel):
    """公式响应"""
    id: str
    name_zh: str
    name_en: str
    formula: str
    latex: str
    category: str
    is_validated: bool
    validation_status: Optional[str]
    created_at: datetime


class SearchResponse(BaseModel):
    """搜索响应"""
    count: int
    results: List[Dict[str, Any]]


class StatisticsResponse(BaseModel):
    """统计响应"""
    total_formulas: int
    total_quantities: int
    validated_count: int
    validation_rate: float
    categories: Dict[str, int]


# ============ 会话管理 ============

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ 健康检查 ============

@app.get("/health", tags=["System"])
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db = SessionLocal()
        db.query(FormulaDB).count()
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Formula Generation System",
            "version": settings.api.version
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# ============ 公式管理 API ============

@app.post("/api/v1/formulas", response_model=Dict[str, Any], tags=["Formulas"])
async def create_formula(
    request: CreateFormulaRequest,
    db: Session = next(get_db())
):
    """创建新公式
    
    **参数描述:**
    - **name_zh**: 中文名称 (e.g., "质能方程")
    - **name_en**: 英文名称 (e.g., "Mass-energy equivalence")
    - **formula_str**: 公式字符串 (e.g., "E = m*c**2")
    - **category**: 分类 (e.g., "相对论")
    
    **响应示例:**
    ```json
    {
      "success": true,
      "id": "fm_0001",
      "message": "公式创建成功",
      "formula": {...}
    }
    ```
    """
    try:
        service = FormulaService(db)
        result = service.create_formula(
            name_zh=request.name_zh,
            name_en=request.name_en,
            formula_str=request.formula_str,
            category=request.category,
            description_zh=request.description_zh or "",
            description_en=request.description_en or "",
            latex_str=request.latex_str or "",
            applications=request.applications,
            notes=request.notes or ""
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        logger.info(f"Formula created: {result['id']}")
        return result
    
    except Exception as e:
        logger.error(f"Error creating formula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/formulas/{formula_id}", response_model=Dict[str, Any], tags=["Formulas"])
async def get_formula(
    formula_id: str,
    db: Session = next(get_db())
):
    """获取公式详情
    
    **参数:**
    - **formula_id**: 公式ID (e.g., "fm_0001")
    
    **特性:**
    - 返回包含量纲检查和推导信息
    - 支持高效缓存
    """
    try:
        service = FormulaService(db)
        formula = service.get_formula(formula_id)
        
        if not formula:
            raise HTTPException(status_code=404, detail="Formula not found")
        
        return {
            "success": True,
            "data": formula
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting formula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/formulas", response_model=SearchResponse, tags=["Formulas"])
async def search_formulas(
    keyword: str = Query(..., min_length=1, description="搜索关键字"),
    search_type: str = Query("all", description="搜索类型: all, name, description, category"),
    category: Optional[str] = Query(None, description="可选的分类过滤"),
    limit: int = Query(50, ge=1, le=100, description="结果数量限制"),
    db: Session = next(get_db())
):
    """搜索公式
    
    **搜索例子:**
    - `GET /api/v1/formulas?keyword=能量`
    - `GET /api/v1/formulas?keyword=能量&category=相对论`
    - `GET /api/v1/formulas?keyword=E&search_type=name`
    """
    try:
        service = FormulaService(db)
        result = service.search_formulas(
            keyword=keyword,
            search_type=search_type,
            category=category,
            limit=limit
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return SearchResponse(
            count=result['count'],
            results=result['results']
        )
    
    except Exception as e:
        logger.error(f"Error searching formulas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 量纲验证 API ============

@app.post("/api/v1/formulas/validate-dimension", response_model=Dict[str, Any], tags=["Validation"])
async def validate_dimension(
    request: ValidateDimensionRequest,
    db: Session = next(get_db())
):
    """深度量纲验证
    
    **批核公式的量纲是否一致**
    
    **请求例子:**
    ```json
    {
      "formula_str": "E = m*c**2"
    }
    ```
    
    **响应示例（一致）:**
    ```json
    {
      "is_consistent": true,
      "match_percentage": 100.0,
      "left_dimension": "ML²T⁻²",
      "right_dimension": "ML²T⁻²",
      "diagnosis": {
        "status": "OK",
        "messages": ["✓ 公式量纲一致"]
      }
    }
    ```
    """
    try:
        validator = DeepDimensionValidator()
        result = validator.validate_formula(request.formula_str)
        
        logger.info(f"Dimension validation: {result['is_consistent']}")
        return result
    
    except Exception as e:
        logger.error(f"Error validating dimension: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/formulas/{formula_id}/validate", response_model=Dict[str, Any], tags=["Validation"])
async def validate_formula_by_id(
    formula_id: str,
    db: Session = next(get_db())
):
    """验证公式量纲（数据库中的公式）
    
    **批核数据库中存储的公式**
    
    **参数:**
    - **formula_id**: 公式ID
    
    **特性:**
    - 自动保存验证结果到数据库
    - 更新公式的验证状态
    """
    try:
        service = FormulaService(db)
        result = service.validate_formula_dimension(formula_id)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        logger.info(f"Formula {formula_id} validated")
        return result
    
    except Exception as e:
        logger.error(f"Error validating formula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 公式推导 API ============

@app.post("/api/v1/formulas/{formula_id}/derive", response_model=Dict[str, Any], tags=["Derivation"])
async def derive_formula(
    formula_id: str,
    request: DeriveFormulaRequest,
    background_tasks: BackgroundTasks,
    db: Session = next(get_db())
):
    """推导公式（求导、积分、求解）
    
    **操作类型:**
    - **derivative**: 求导 (e.g., 对 t 求一阶导)
    - **integrate**: 积分 (e.g., 对 t 积分)
    - **solve**: 求解 (e.g., 解出 m)
    
    **请求例子:**
    ```json
    {
      "operation": "derivative",
      "variable": "t",
      "order": 1
    }
    ```
    
    **响应示例:**
    ```json
    {
      "success": true,
      "operation": "derivative",
      "source": "E = m*c**2",
      "result": "0",
      "steps": ["\u5bf9 t \u6c42 1 \u9636\u5bfc"]
    }
    ```
    """
    try:
        service = FormulaService(db)
        result = service.derive_formula(
            formula_id=formula_id,
            operation=request.operation,
            variable=request.variable,
            order=request.order
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        logger.info(f"Formula {formula_id} derived: {request.operation}")
        return result
    
    except Exception as e:
        logger.error(f"Error deriving formula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 统计 API ============

@app.get("/api/v1/statistics", response_model=StatisticsResponse, tags=["Statistics"])
async def get_statistics(
    db: Session = next(get_db())
):
    """获取统计信息
    
    **返回信息:**
    - 总公式数
    - 总物理量数
    - 已验证公式数
    - 验证成功率
    - 按分类的公式数量
    """
    try:
        service = FormulaService(db)
        stats = service.get_statistics()
        
        return StatisticsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/formulas/category/{category}", response_model=SearchResponse, tags=["Formulas"])
async def get_formulas_by_category(
    category: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = next(get_db())
):
    """按分类获取公式
    
    **请求例子:**
    - `GET /api/v1/formulas/category/相对论`
    - `GET /api/v1/formulas/category/力学?limit=100`
    """
    try:
        service = FormulaService(db)
        formulas = service.get_formulas_by_category(category)
        
        return SearchResponse(
            count=len(formulas),
            results=formulas[:limit]
        )
    
    except Exception as e:
        logger.error(f"Error getting formulas by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/formulas/recent", response_model=SearchResponse, tags=["Formulas"])
async def get_recent_formulas(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=100),
    db: Session = next(get_db())
):
    """获取最近添加的公式
    
    **参数:**
    - **days**: 日期范围 (1-90天)
    - **limit**: 结果数量限制
    """
    try:
        service = FormulaService(db)
        formulas = service.get_recent_formulas(days)
        
        return SearchResponse(
            count=len(formulas),
            results=formulas[:limit]
        )
    
    except Exception as e:
        logger.error(f"Error getting recent formulas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 错误处理 ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """自定义 HTTP 错误处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
