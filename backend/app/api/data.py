"""
Data Management API
数据管理接口 - 文件上传、数据导入、数据查询
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import json
import pandas as pd

from ..database import get_db
from ..models.movie import Movie
from ..schemas.movie import MovieCreate, MovieUpdate, MovieResponse, MovieListResponse, MovieStatsResponse
from ..schemas.data import FileUploadResponse, DataImportRequest, DataImportResponse, DataCleanRequest, DataCleanResponse
from ..services.data_import import data_import_service
from ..services.data_cleaner import data_cleaner

router = APIRouter(prefix="/api/data", tags=["数据管理"])


def _auto_detect_mapping(columns: List[str]) -> Dict[str, str]:
    """根据列名自动检测字段映射"""
    mapping = {}
    columns_lower = {col.lower(): col for col in columns}

    # 电影名称映射
    for key in ['片名', '电影名称', '电影名', '名称', 'title', 'name']:
        if key in columns:
            mapping['title'] = key
            break
    if 'title' not in mapping and '片名' in columns_lower:
        mapping['title'] = columns_lower['片名']

    # 票房映射
    for key in ['票房(万元)', '票房', '总票房', '累计票房', 'box_office']:
        if key in columns:
            mapping['box_office_wan'] = key
            break

    # 年份映射
    for key in ['上映年份', '年份', 'year', '上映日期']:
        if key in columns:
            mapping['release_year'] = key
            break

    # 类型映射
    for key in ['类型', '电影类型', '类型/版本', 'type']:
        if key in columns:
            mapping['type'] = key
            break

    # 评分映射
    for key in ['评分', '豆瓣评分', 'rating']:
        if key in columns:
            mapping['rating'] = key
            break

    # 评分人数映射
    for key in ['评分人数', '观众评分人数', 'rating_count']:
        if key in columns:
            mapping['rating_count'] = key
            break

    # 想看人数映射
    for key in ['想看人数', 'wish_count']:
        if key in columns:
            mapping['wish_count'] = key
            break

    # 平均票价映射
    for key in ['平均票价', 'avg_price']:
        if key in columns:
            mapping['avg_price'] = key
            break

    # 场均人次映射
    for key in ['场均人次', 'per_session_attendance']:
        if key in columns:
            mapping['per_session_attendance'] = key
            break

    # 排名映射
    for key in ['排名', 'ranking']:
        if key in columns:
            mapping['ranking'] = key
            break

    # 上榜年份映射
    for key in ['上榜年份', 'list_year']:
        if key in columns:
            mapping['list_year'] = key
            break

    # 电影ID映射
    for key in ['电影id', 'movie_id', 'id']:
        if key in columns:
            mapping['movie_id'] = key
            break

    return mapping


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...)
):
    """
    上传数据文件（Excel或CSV）

    支持格式：
    - .xlsx, .xls - Excel文件
    - .csv - CSV文件

    返回文件预览数据供用户确认
    """
    # 验证文件扩展名
    from ..config import settings
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。仅支持: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 读取文件内容
    content = await file.read()

    # 检查文件大小
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大。最大支持 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )

    try:
        # 保存并解析文件
        file_id, df = data_import_service.save_uploaded_file(file.filename, content)

        # 获取预览数据（前10条）
        preview = df.head(10).fillna("").to_dict('records')

        # 获取列信息
        columns = df.columns.tolist()

        # 获取推荐映射（基于文件名和列名）
        suggested_mapping = data_import_service.get_template_mapping(file.filename)

        # 如果没有预设映射，尝试根据列名自动映射
        if not suggested_mapping:
            suggested_mapping = _auto_detect_mapping(columns)

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            total_rows=len(df),
            columns=columns,
            preview=preview,
            file_path=f"{settings.UPLOAD_DIR}/{file_id}{file_ext}",
            suggested_mapping=suggested_mapping
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")


@router.post("/clean", response_model=DataCleanResponse)
async def clean_data(
    request: DataCleanRequest
):
    """
    对指定列的数据进行清理

    参数：
    - file_id: 文件ID
    - column: 要清理的列名
    - clean_type: 清理类型 (box_office, year, percentage, people_count, type, etc.)

    返回清理后的数据预览，并更新后端缓存
    """
    try:
        # 获取文件数据
        df = data_import_service.get_file_data(request.file_id)
        if df is None:
            raise HTTPException(status_code=404, detail=f"文件不存在或已过期: {request.file_id}")

        # 检查列是否存在
        if request.column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"列不存在: {request.column}，可用列: {', '.join(df.columns)}"
            )

        # 获取原始数据
        original_data = df[request.column].tolist()

        # 清理数据
        cleaned_data, errors = data_cleaner.clean_column(original_data, request.clean_type)

        # 更新缓存的DataFrame
        df[request.column] = cleaned_data

        # 统计成功和失败数量
        success_count = sum(1 for i, (o, c) in enumerate(zip(original_data, cleaned_data))
                           if not pd.isna(o) and c is not None)
        failed_count = len(errors)

        return DataCleanResponse(
            original=original_data[:10],  # 返回前10条预览
            cleaned=cleaned_data[:10],
            success_count=success_count,
            failed_count=failed_count,
            errors=errors[:10]  # 只返回前10个错误
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.post("/import", response_model=DataImportResponse)
async def import_data(
    request: DataImportRequest,
    db: Session = Depends(get_db)
):
    """
    导入数据到数据库

    根据用户提供的字段映射，将文件数据导入到数据库
    """
    try:
        result = data_import_service.import_data(
            file_id=request.file_id,
            mapping=request.field_mapping,
            db=db,
            skip_duplicates=request.skip_duplicates,
            data_source=request.data_source
        )

        return DataImportResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/movies", response_model=MovieListResponse)
async def get_movies(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="电影类型筛选"),
    data_source: Optional[str] = Query(None, description="数据来源筛选"),
    db: Session = Depends(get_db)
):
    """
    获取电影列表

    支持分页、搜索、类型筛选和数据来源筛选
    """
    query = db.query(Movie)

    # 搜索过滤
    if search:
        query = query.filter(Movie.title.contains(search))

    # 类型过滤
    if type:
        query = query.filter(Movie.type == type)

    # 数据来源过滤
    if data_source:
        query = query.filter(Movie.data_source == data_source)

    # 获取总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    movies = query.order_by(Movie.id.desc()).offset(offset).limit(page_size).all()

    return MovieListResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[MovieResponse.model_validate(m.to_dict()) for m in movies]
    )


@router.delete("/movies/all")
async def delete_all_movies(
    confirm: bool = Query(False, description="确认删除，需要传true"),
    db: Session = Depends(get_db)
):
    """
    删除所有电影数据（危险操作，需要二次确认）

    参数：
    - confirm: 必须为true才会执行删除
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="请设置confirm=true确认删除")

    from sqlalchemy import func

    # 统计删除数量
    count = db.query(func.count(Movie.id)).scalar() or 0

    # 删除所有电影
    db.query(Movie).delete()
    db.commit()

    return {"message": f"已删除 {count} 部电影"}


@router.get("/movies/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个电影详情
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    return MovieResponse.model_validate(movie.to_dict())


@router.post("/movies", response_model=MovieResponse)
async def create_movie(
    movie: MovieCreate,
    db: Session = Depends(get_db)
):
    """
    手动添加电影
    """
    # 检查是否已存在
    existing = db.query(Movie).filter(Movie.title == movie.title).first()
    if existing:
        raise HTTPException(status_code=400, detail="电影已存在")

    # 创建电影
    from ..models.movie import DataSource
    new_movie = Movie(
        **movie.model_dump(),
        data_source=DataSource.MANUAL
    )

    # 处理tags
    if movie.tags:
        new_movie.tags_list = movie.tags

    db.add(new_movie)
    db.commit()
    db.refresh(new_movie)

    return MovieResponse.model_validate(new_movie.to_dict())


@router.put("/movies/{movie_id}", response_model=MovieResponse)
async def update_movie(
    movie_id: int,
    movie: MovieUpdate,
    db: Session = Depends(get_db)
):
    """
    更新电影信息
    """
    db_movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    # 更新字段
    update_data = movie.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tags" and value is not None:
            db_movie.tags_list = value
        else:
            setattr(db_movie, field, value)

    db.commit()
    db.refresh(db_movie)

    return MovieResponse.model_validate(db_movie.to_dict())


@router.delete("/movies/{movie_id}")
async def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db)
):
    """
    删除电影
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    db.delete(movie)
    db.commit()

    return {"message": "删除成功"}


@router.get("/stats", response_model=MovieStatsResponse)
async def get_stats(
    db: Session = Depends(get_db)
):
    """
    获取数据统计概览
    """
    from sqlalchemy import func, case

    # 总电影数
    total_movies = db.query(func.count(Movie.id)).scalar()

    # 总票房
    total_box_office = db.query(func.sum(Movie.box_office_wan)).scalar() or 0

    # 平均评分
    avg_rating = db.query(func.avg(Movie.rating)).filter(Movie.rating.isnot(None)).scalar()

    # 年份分布
    year_dist = db.query(
        Movie.release_year,
        func.count(Movie.id).label('count')
    ).filter(Movie.release_year.isnot(None)) \
     .group_by(Movie.release_year) \
     .order_by(Movie.release_year.desc()) \
     .all()

    year_distribution = {str(year): count for year, count in year_dist}

    # 类型分布
    type_dist = db.query(
        Movie.type,
        func.count(Movie.id).label('count')
    ).filter(Movie.type.isnot(None)) \
     .group_by(Movie.type) \
     .order_by(func.count(Movie.id).desc()) \
     .limit(10) \
     .all()

    genre_distribution = {type_name: count for type_name, count in type_dist}

    # 数据来源分布
    source_dist = db.query(
        Movie.data_source,
        func.count(Movie.id).label('count')
    ).group_by(Movie.data_source).all()

    data_source_distribution = {source.value: count for source, count in source_dist}

    return MovieStatsResponse(
        total_movies=total_movies,
        total_box_office=round(total_box_office, 2),
        avg_rating=round(avg_rating, 2) if avg_rating else None,
        year_distribution=year_distribution,
        genre_distribution=genre_distribution,
        data_source_distribution=data_source_distribution
    )


@router.post("/export")
async def export_data(
    db: Session = Depends(get_db)
):
    """
    导出所有电影数据为Excel文件
    """
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from datetime import datetime

    # 查询所有电影
    movies = db.query(Movie).all()

    # 转换为DataFrame
    data = [m.to_dict() for m in movies]
    df = pd.DataFrame(data)

    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='电影数据')

    output.seek(0)

    # 生成文件名
    filename = f"电影数据导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/template")
async def download_template():
    """
    下载数据导入模板
    """
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    # 创建模板
    template_data = {
        "片名": ["示例电影1", "示例电影2"],
        "上映年份": [2024, 2024],
        "票房(万元)": [10000, 5000],
        "平均票价": [35.0, 40.0],
        "场均人次": [30, 25],
        "排名": [1, 2],
        "上榜年份": [2024, 2024],
        "电影类型": ["剧情", "喜剧"],
        "豆瓣评分": [7.5, 6.8],
        "评分人数": [10000, 5000]
    }

    df = pd.DataFrame(template_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='电影数据模板')

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=电影数据导入模板.xlsx"}
    )
