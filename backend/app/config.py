"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "豆瓣电影票房预测系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./doubanban.db"  # 使用SQLite便于开发

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # File Upload
    UPLOAD_DIR: str = "temp"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv"}

    # ML Model
    MODEL_DIR: str = "ml_models"
    DATA_DIR: str = "data"

    # Crawler Settings
    CRAWL_DELAY: float = 2.0
    CRAWL_TIMEOUT: int = 30
    CRAWL_MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
