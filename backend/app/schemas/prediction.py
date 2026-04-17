"""
Prediction Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MovieInfo(BaseModel):
    """Movie basic info"""
    id: int
    title: str

    class Config:
        from_attributes = True


class PredictionCreate(BaseModel):
    """Prediction creation schema"""
    movie_id: Optional[int] = None
    model_type: str = Field(..., description="模型类型: lr, xgboost, transformer")

    # 输入特征（用于新电影预测）
    title: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    wish_count: Optional[int] = None
    type: Optional[str] = None
    release_year: Optional[int] = None
    avg_price: Optional[float] = None


class PredictionResponse(BaseModel):
    """Prediction response schema"""
    id: int
    movie_id: Optional[int]
    model_type: str
    predicted_box_office: Optional[float]
    predicted_box_office_wan: Optional[float]
    confidence_lower: Optional[float]
    confidence_upper: Optional[float]
    feature_importance: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    movie: Optional[MovieInfo] = None

    class Config:
        from_attributes = True


class PredictionCompareResponse(BaseModel):
    """Prediction comparison response"""
    movie_title: str
    actual_box_office: Optional[int]
    predictions: Dict[str, Any]
