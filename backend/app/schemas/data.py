"""
Data Import Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class FileUploadResponse(BaseModel):
    """File upload response"""
    file_id: str
    filename: str
    total_rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]
    file_path: str
    suggested_mapping: Optional[Dict[str, str]] = None


class DataPreviewResponse(BaseModel):
    """Data preview response"""
    total_rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]
    data_types: Dict[str, str]
    sample_stats: Optional[Dict[str, Any]] = None


class FieldMapping(BaseModel):
    """Field mapping for data import"""
    title: Optional[str] = Field(None, description="电影名称字段")
    release_year: Optional[str] = Field(None, description="上映年份字段")
    box_office: Optional[str] = Field(None, description="票房字段（元）")
    box_office_wan: Optional[str] = Field(None, description="票房字段（万元）")
    avg_price: Optional[str] = Field(None, description="平均票价字段")
    per_session_attendance: Optional[str] = Field(None, description="场均人次字段")
    ranking: Optional[str] = Field(None, description="排名字段")
    list_year: Optional[str] = Field(None, description="上榜年份字段")
    movie_id: Optional[str] = Field(None, description="电影ID字段")
    type: Optional[str] = Field(None, description="电影类型字段")
    rating: Optional[str] = Field(None, description="评分字段")
    rating_count: Optional[str] = Field(None, description="评分人数字段")
    wish_count: Optional[str] = Field(None, description="想看人数字段")
    tags: Optional[str] = Field(None, description="标签字段")
    release_date: Optional[str] = Field(None, description="上映日期字段")


class DataImportRequest(BaseModel):
    """Data import request"""
    file_id: str
    field_mapping: FieldMapping
    skip_duplicates: bool = True
    data_source: str = "upload"

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "temp_file_123",
                "field_mapping": {
                    "title": "片名",
                    "release_year": "上映年份",
                    "box_office_wan": "票房(万元)",
                    "avg_price": "平均票价",
                    "per_session_attendance": "场均人次",
                    "ranking": "排名",
                    "list_year": "上榜年份"
                },
                "skip_duplicates": True,
                "data_source": "upload"
            }
        }


class DataImportResponse(BaseModel):
    """Data import response"""
    success: bool
    total_rows: int
    imported_count: int
    skipped_count: int
    failed_count: int
    errors: List[str] = []
    task_id: Optional[int] = None


class DataCleanRequest(BaseModel):
    """Data clean request"""
    file_id: str = Field(..., description="文件ID")
    column: str = Field(..., description="要清理的列名")
    clean_type: str = Field(..., description="清理类型")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "temp_abc123",
                "column": "上映年份",
                "clean_type": "year"
            }
        }


class DataCleanResponse(BaseModel):
    """Data clean response"""
    original: List[Any] = Field(..., description="原始数据预览（前10条）")
    cleaned: List[Any] = Field(..., description="清理后数据预览（前10条）")
    success_count: int = Field(..., description="成功清理的数量")
    failed_count: int = Field(..., description="失败的数量")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")
