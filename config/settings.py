"""
应用配置管理
支持多环境配置、环境变量覆盖
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    driver: str = "postgresql"
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "password")
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "formula_db")
    
    @property
    def url(self) -> str:
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis缓存配置"""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class MLSettings(BaseSettings):
    """机器学习配置"""
    model_name: str = os.getenv("ML_MODEL_NAME", "google/mt5-base")
    device: str = os.getenv("ML_DEVICE", "cuda")  # cuda 或 cpu
    max_length: int = int(os.getenv("ML_MAX_LENGTH", "512"))
    batch_size: int = int(os.getenv("ML_BATCH_SIZE", "32"))
    learning_rate: float = float(os.getenv("ML_LEARNING_RATE", "5e-5"))
    epochs: int = int(os.getenv("ML_EPOCHS", "3"))
    model_cache_dir: str = os.getenv("ML_MODEL_CACHE", "./models")


class APISettings(BaseSettings):
    """API配置"""
    title: str = "冯德建公式系统 API"
    version: str = "2.0.0"
    description: str = "完整的物理公式建模、生成和验证系统"
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("API_DEBUG", "False").lower() == "true"
    
    # 跨域配置
    cors_origins: list = ["*"]
    cors_credentials: bool = True
    cors_methods: list = ["*"]
    cors_headers: list = ["*"]


class Settings(BaseSettings):
    """全局应用配置"""
    # 环境
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = environment == "development"
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    ml: MLSettings = MLSettings()
    api: APISettings = APISettings()
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 缓存配置
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL", "3600"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()
