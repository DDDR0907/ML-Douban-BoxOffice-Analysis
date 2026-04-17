"""
FastAPI Main Application
豆瓣电影票房预测系统 - 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .api import data_router, crawl_router, model_router, predict_router, visualize_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    print("✅ 数据库初始化完成")
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功!")
    yield
    # 关闭时的清理工作
    print("👋 应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于机器学习的豆瓣电影票房预测及可视化分析系统",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data_router)
app.include_router(crawl_router)
app.include_router(model_router)
app.include_router(predict_router)
app.include_router(visualize_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "基于机器学习的豆瓣电影票房预测及可视化分析系统",
        "docs": "/docs",
        "endpoints": {
            "data": "/api/data",
            "crawl": "/api/crawl",
            "model": "/api/model",
            "predict": "/api/predict",
            "visualize": "/api/visualize"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
