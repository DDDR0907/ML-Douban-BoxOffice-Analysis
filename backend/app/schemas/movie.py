"""
Movie Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MovieBase(BaseModel):
    """Base movie schema"""
    title: str = Field(..., description="电影名称")
    type: Optional[str] = Field(None, description="电影类型")
    release_year: Optional[int] = Field(None, description="上映年份")
    release_date: Optional[str] = Field(None, description="上映日期")


class MovieCreate(MovieBase):
    """Movie creation schema"""
    douban_id: Optional[str] = None
    movie_id: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10, description="豆瓣评分")
    rating_count: Optional[int] = Field(None, ge=0, description="评分人数")
    wish_count: Optional[int] = Field(None, ge=0, description="想看人数")
    tags: Optional[List[str]] = None
    topic_heat: Optional[int] = None
    box_office: Optional[int] = Field(None, ge=0, description="票房（元）")
    box_office_wan: Optional[float] = Field(None, ge=0, description="票房（万元）")
    avg_price: Optional[float] = Field(None, ge=0, description="平均票价")
    per_session_attendance: Optional[int] = Field(None, ge=0, description="场均人次")
    ranking: Optional[int] = None
    list_year: Optional[int] = None
    positive_ratio: Optional[float] = Field(None, ge=0, le=100, description="正面评价比例")
    data_source: str = "manual"
    original_language: Optional[str] = None
    production_countries: Optional[str] = None


class MovieUpdate(BaseModel):
    """Movie update schema"""
    title: Optional[str] = None
    type: Optional[str] = None
    release_year: Optional[int] = None
    release_date: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10)
    rating_count: Optional[int] = Field(None, ge=0)
    wish_count: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    topic_heat: Optional[int] = None
    box_office: Optional[int] = Field(None, ge=0)
    box_office_wan: Optional[float] = Field(None, ge=0)
    avg_price: Optional[float] = Field(None, ge=0)
    per_session_attendance: Optional[int] = Field(None, ge=0)
    ranking: Optional[int] = None
    list_year: Optional[int] = None
    positive_ratio: Optional[float] = Field(None, ge=0, le=100)


class MovieResponse(MovieBase):
    """Movie response schema"""
    id: int
    douban_id: Optional[str]
    movie_id: Optional[str]
    rating: Optional[float]
    rating_count: Optional[int]
    wish_count: Optional[int]
    tags: Optional[List[str]]
    topic_heat: Optional[int]
    box_office: Optional[int]
    box_office_wan: Optional[float]
    avg_price: Optional[float]
    per_session_attendance: Optional[int]
    ranking: Optional[int]
    list_year: Optional[int]
    positive_ratio: Optional[float]
    data_source: str
    original_language: Optional[str]
    production_countries: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    """Movie list response"""
    total: int
    page: int
    page_size: int
    data: List[MovieResponse]


class MovieStatsResponse(BaseModel):
    """Movie statistics response"""
    total_movies: int
    total_box_office: float
    avg_rating: Optional[float]
    year_distribution: dict
    genre_distribution: dict
    data_source_distribution: dict
