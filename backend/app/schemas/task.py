"""
Task Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TaskCreate(BaseModel):
    """Task creation schema"""
    task_type: str = Field(..., description="任务类型: crawl, preprocess, train, predict, import")
    config: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Task response schema"""
    id: int
    task_type: str
    status: str
    progress: int
    current_step: Optional[str]
    result: Optional[Dict[str, Any]]
    error_msg: Optional[str]
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
