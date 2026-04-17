"""
Crawler API
爬虫相关接口 - 启动爬取、查询状态、配置管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import threading
import asyncio

from ..database import get_db
from ..models.task import Task, TaskType, TaskStatus
from ..schemas.task import TaskResponse
from ..services.crawler import crawler_task_manager

router = APIRouter(prefix="/api/crawl", tags=["数据爬取"])


def run_crawl_task_thread(task_id: int, year_start: int, year_end: int, min_rating: float, max_movies: int):
    """
    在新线程中运行爬虫任务

    Args:
        task_id: 任务ID
        year_start: 起始年份
        year_end: 结束年份
        min_rating: 最低评分
        max_movies: 最大爬取数量
    """
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 运行异步爬虫任务
        loop.run_until_complete(
            crawler_task_manager.run_crawl_task(
                task_id, year_start, year_end, min_rating, max_movies
            )
        )
    finally:
        loop.close()


@router.post("/start", response_model=TaskResponse)
async def start_crawl(
    year_start: int = Query(2010, description="起始年份"),
    year_end: int = Query(2024, description="结束年份"),
    min_rating: float = Query(5.0, description="最低评分"),
    max_movies: int = Query(5000, description="最大爬取数量"),
    db: Session = Depends(get_db)
):
    """
    开始爬取豆瓣电影数据

    参数：
    - year_start: 起始年份（默认2010）
    - year_end: 结束年份（默认2024）
    - min_rating: 最低豆瓣评分（默认5.0）
    - max_movies: 最大爬取数量（默认5000）
    """
    # 检查是否有正在运行的爬虫任务
    running_task = db.query(Task).filter(
        Task.task_type == TaskType.CRAWL,
        Task.status == TaskStatus.RUNNING
    ).first()

    if running_task:
        raise HTTPException(status_code=400, detail="已有爬虫任务正在运行")

    # 创建爬取任务
    task = Task(
        task_type=TaskType.CRAWL,
        status=TaskStatus.PENDING,
        config_dict={
            "year_start": year_start,
            "year_end": year_end,
            "min_rating": min_rating,
            "max_movies": max_movies
        }
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 启动后台爬虫任务
    thread = threading.Thread(
        target=run_crawl_task_thread,
        args=(task.id, year_start, year_end, min_rating, max_movies)
    )
    thread.daemon = True
    thread.start()

    return TaskResponse.model_validate(task.to_dict())


@router.get("/status", response_model=TaskResponse)
async def get_crawl_status(
    task_id: Optional[int] = Query(None, description="任务ID"),
    db: Session = Depends(get_db)
):
    """
    获取爬取任务状态

    如果不提供task_id，返回最新的爬取任务状态
    """
    query = db.query(Task).filter(Task.task_type == TaskType.CRAWL)

    if task_id:
        query = query.filter(Task.id == task_id)
    else:
        # 获取最新的任务
        query = query.order_by(Task.id.desc())

    task = query.first()

    if not task:
        raise HTTPException(status_code=404, detail="未找到爬取任务")

    return TaskResponse.model_validate(task.to_dict())


@router.post("/stop")
async def stop_crawl(
    db: Session = Depends(get_db)
):
    """
    停止当前运行的爬虫任务
    """
    # 查找正在运行的任务
    task = db.query(Task).filter(
        Task.task_type == TaskType.CRAWL,
        Task.status == TaskStatus.RUNNING
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="没有正在运行的爬虫任务")

    # 更新任务状态为失败（用户手动停止）
    task.status = TaskStatus.FAILED
    task.error_msg = "用户手动停止"
    task.current_step = "已停止"
    db.commit()

    # 注意：由于爬虫运行在独立线程中，这里只是标记任务状态
    # 实际的爬虫会检查任务状态并停止

    return {"message": "爬虫任务已停止", "task_id": task.id}


@router.get("/config")
async def get_crawl_config():
    """
    获取爬虫配置
    """
    from ..config import settings

    return {
        "crawl_delay": settings.CRAWL_DELAY,
        "crawl_timeout": settings.CRAWL_TIMEOUT,
        "crawl_max_retries": settings.CRAWL_MAX_RETRIES
    }


@router.put("/config")
async def update_crawl_config(
    crawl_delay: Optional[float] = None,
    crawl_timeout: Optional[int] = None,
    crawl_max_retries: Optional[int] = None
):
    """
    更新爬虫配置
    """
    # TODO: 更新配置文件或数据库
    return {
        "message": "配置更新成功",
        "config": {
            "crawl_delay": crawl_delay,
            "crawl_timeout": crawl_timeout,
            "crawl_max_retries": crawl_max_retries
        }
    }


@router.get("/history")
async def get_crawl_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取爬取历史记录
    """
    query = db.query(Task).filter(Task.task_type == TaskType.CRAWL)

    total = query.count()

    offset = (page - 1) * page_size
    tasks = query.order_by(Task.id.desc()).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [TaskResponse.model_validate(t.to_dict()) for t in tasks]
    }
