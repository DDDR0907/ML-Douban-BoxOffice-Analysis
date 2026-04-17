"""
API Routes
"""
from .data import router as data_router
from .crawl import router as crawl_router
from .model import router as model_router
from .predict import router as predict_router
from .visualize import router as visualize_router

__all__ = [
    "data_router",
    "crawl_router",
    "model_router",
    "predict_router",
    "visualize_router",
]
