"""
Visualization API
可视化接口 - 提供各类图表数据
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import json

from ..database import get_db
from ..models.movie import Movie
from ..services.model_utils import get_model_feature_importance

router = APIRouter(prefix="/api/visualize", tags=["数据可视化"])


@router.get("/rating-boxoffice")
async def rating_boxoffice_scatter(
    db: Session = Depends(get_db)
):
    """
    豆瓣评分 - 票房散点图数据
    """
    movies = db.query(Movie).filter(
        Movie.rating.isnot(None),
        Movie.box_office_wan.isnot(None)
    ).limit(500).all()  # 限制数量以提高性能

    data = [
        {
            "x": m.rating,
            "y": m.box_office_wan,
            "title": m.title,
            "type": m.type,
            "year": m.release_year
        }
        for m in movies
    ]

    return {
        "chart_type": "scatter",
        "x_axis": "豆瓣评分",
        "y_axis": "票房（万元）",
        "data": data
    }


@router.get("/genre-distribution")
async def genre_boxoffice_distribution(
    db: Session = Depends(get_db)
):
    """
    不同类型电影票房分布箱线图数据
    """
    movies = db.query(Movie).filter(
        Movie.type.isnot(None),
        Movie.box_office_wan.isnot(None)
    ).all()

    # 按类型分组
    genre_data = {}
    for m in movies:
        if m.type:
            if m.type not in genre_data:
                genre_data[m.type] = []
            genre_data[m.type].append(m.box_office_wan)

    # 转换为图表数据格式
    data = [
        {
            "type": genre,
            "values": values,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "median": sorted(values)[len(values)//2] if values else 0,
            "q1": sorted(values)[len(values)//4] if len(values) > 4 else 0,
            "q3": sorted(values)[len(values)*3//4] if len(values) > 4 else 0,
        }
        for genre, values in genre_data.items()
        if len(values) >= 5  # 至少5部电影
    ]

    # 按中位数排序
    data.sort(key=lambda x: x["median"], reverse=True)

    return {
        "chart_type": "boxplot",
        "x_axis": "电影类型",
        "y_axis": "票房（万元）",
        "data": data[:10]  # 只返回前10个类型
    }


@router.get("/model-comparison")
async def model_performance_comparison(
    db: Session = Depends(get_db)
):
    """
    模型性能对比图数据
    """
    from ..config import settings
    from pathlib import Path
    import joblib

    model_dir = Path(settings.MODEL_DIR)

    if not model_dir.exists():
        return {
            "chart_type": "bar",
            "metrics": ["R²", "RMSE", "MAE"],
            "models": {},
            "message": "暂无训练模型"
        }

    models = {}

    # 查找所有模型文件
    for model_type in ["lr", "xgboost"]:
        model_files = list(model_dir.glob(f"{model_type}_*.pkl"))
        if model_files:
            try:
                latest = max(model_files, key=lambda p: p.stat().st_mtime)
                model_data = joblib.load(latest)
                metrics = model_data.get('metrics', {})

                # 获取测试集指标
                test_metrics = model_data.get('test_metrics', metrics)

                model_name = "XGBoost" if model_type == "xgboost" else "线性回归"
                models[model_name] = {
                    "R²": round(test_metrics.get('r2_score', 0), 4),
                    "RMSE": round(test_metrics.get('rmse', 0), 2),
                    "MAE": round(test_metrics.get('mae', 0), 2)
                }
            except Exception as e:
                print(f"加载模型 {model_type} 失败: {e}")

    return {
        "chart_type": "bar",
        "metrics": ["R²", "RMSE", "MAE"],
        "models": models
    }


@router.get("/feature-importance")
async def feature_importance(
    model_type: str = Query("xgboost", description="模型类型"),
    db: Session = Depends(get_db)
):
    """
    特征重要性数据
    """
    from ..config import settings
    from pathlib import Path
    import joblib

    model_dir = Path(settings.MODEL_DIR)

    if not model_dir.exists():
        return {
            "model_type": model_type,
            "chart_type": "horizontal_bar",
            "data": [],
            "message": "暂无训练模型"
        }

    # 查找模型文件
    model_files = list(model_dir.glob(f"{model_type}_*.pkl"))

    if not model_files:
        return {
            "model_type": model_type,
            "chart_type": "horizontal_bar",
            "data": [],
            "message": f"未找到 {model_type} 模型"
        }

    try:
        latest = max(model_files, key=lambda p: p.stat().st_mtime)
        model_data = joblib.load(latest)
        importance_dict = get_model_feature_importance(model_data)

        # 转换为图表格式
        data = [
            {
                "feature": feature,
                "importance": round(value * 100, 2)  # 转为百分比
            }
            for feature, value in importance_dict.items()
        ]

        # 按重要性排序
        data.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "model_type": model_type,
            "chart_type": "horizontal_bar",
            "data": data[:15]  # 返回前15个特征
        }

    except Exception as e:
        return {
            "model_type": model_type,
            "chart_type": "horizontal_bar",
            "data": [],
            "error": str(e)
        }


@router.get("/predict-comparison")
async def predict_vs_actual(
    movie_id: Optional[int] = Query(None, description="指定电影ID"),
    limit: int = Query(20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    预测vs实际票房对比图数据
    """
    # TODO: 从预测记录中获取数据
    from ..models.prediction import Prediction

    query = db.query(Prediction).filter(
        Prediction.movie_id.isnot(None),
        Prediction.predicted_box_office.isnot(None)
    )

    if movie_id:
        query = query.filter(Prediction.movie_id == movie_id)

    predictions = query.order_by(Prediction.id.desc()).limit(limit).all()

    data = []
    for pred in predictions:
        if pred.movie:
            data.append({
                "title": pred.movie.title,
                "actual": pred.movie.box_office_wan,
                "predicted": pred.predicted_box_office_wan,
                "model_type": pred.model_type.value
            })

    return {
        "chart_type": "line",
        "data": data
    }


@router.get("/year-trend")
async def boxoffice_year_trend(
    db: Session = Depends(get_db)
):
    """
    年度票房趋势图数据
    """
    from sqlalchemy import func

    results = db.query(
        Movie.release_year,
        func.sum(Movie.box_office_wan).label('total_box_office'),
        func.count(Movie.id).label('movie_count'),
        func.avg(Movie.rating).label('avg_rating')
    ).filter(
        Movie.release_year.isnot(None),
        Movie.box_office_wan.isnot(None)
    ).group_by(
        Movie.release_year
    ).order_by(
        Movie.release_year
    ).all()

    data = [
        {
            "year": int(year),
            "total_box_office": round(float(total), 2),
            "movie_count": count,
            "avg_rating": round(float(rating), 2) if rating else None
        }
        for year, total, count, rating in results
    ]

    return {
        "chart_type": "line",
        "x_axis": "年份",
        "data": data
    }


@router.get("/top-movies")
async def top_movies(
    by: str = Query("box_office", description="排序字段: box_office, rating"),
    limit: int = Query(20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    Top电影榜单数据
    """
    query = db.query(Movie)

    if by == "box_office":
        query = query.filter(Movie.box_office_wan.isnot(None))
        query = query.order_by(Movie.box_office_wan.desc())
    elif by == "rating":
        query = query.filter(Movie.rating.isnot(None))
        query = query.order_by(Movie.rating.desc())

    movies = query.limit(limit).all()

    data = [
        {
            "rank": idx + 1,
            "title": m.title,
            "box_office": m.box_office_wan,
            "rating": m.rating,
            "year": m.release_year,
            "type": m.type
        }
        for idx, m in enumerate(movies)
    ]

    return {
        "by": by,
        "data": data
    }


@router.get("/data-overview")
async def data_overview(
    db: Session = Depends(get_db)
):
    """
    数据概览统计
    """
    from sqlalchemy import func
    from ..models.prediction import Prediction
    from ..models.task import Task

    # 电影统计
    total_movies = db.query(func.count(Movie.id)).scalar()
    movies_with_box_office = db.query(func.count(Movie.id)).filter(
        Movie.box_office_wan.isnot(None)
    ).scalar()
    movies_with_rating = db.query(func.count(Movie.id)).filter(
        Movie.rating.isnot(None)
    ).scalar()

    # 票房统计
    box_office_stats = db.query(
        func.min(Movie.box_office_wan).label('min'),
        func.max(Movie.box_office_wan).label('max'),
        func.avg(Movie.box_office_wan).label('avg')
    ).filter(
        Movie.box_office_wan.isnot(None)
    ).first()

    # 评分统计
    rating_stats = db.query(
        func.min(Movie.rating).label('min'),
        func.max(Movie.rating).label('max'),
        func.avg(Movie.rating).label('avg')
    ).filter(
        Movie.rating.isnot(None)
    ).first()

    # 预测统计
    total_predictions = db.query(func.count(Prediction.id)).scalar()

    # 数据来源统计
    data_source_stats = db.query(
        Movie.data_source,
        func.count(Movie.id).label('count')
    ).group_by(
        Movie.data_source
    ).all()

    # 年份分布
    year_distribution = db.query(
        Movie.release_year,
        func.count(Movie.id).label('count')
    ).filter(
        Movie.release_year.isnot(None)
    ).group_by(
        Movie.release_year
    ).order_by(
        Movie.release_year
    ).all()

    return {
        "movies": {
            "total": total_movies,
            "with_box_office": movies_with_box_office,
            "with_rating": movies_with_rating,
            "completion_rate": round(movies_with_box_office / total_movies * 100, 2) if total_movies > 0 else 0
        },
        "box_office": {
            "min": round(float(box_office_stats.min or 0), 2),
            "max": round(float(box_office_stats.max or 0), 2),
            "avg": round(float(box_office_stats.avg or 0), 2)
        },
        "rating": {
            "min": round(float(rating_stats.min or 0), 2),
            "max": round(float(rating_stats.max or 0), 2),
            "avg": round(float(rating_stats.avg or 0), 2)
        },
        "predictions": {
            "total": total_predictions
        },
        "data_sources": [
            {"source": source.value if source else "unknown", "count": count}
            for source, count in data_source_stats
        ],
        "years": [
            {"year": int(year), "count": count}
            for year, count in year_distribution
        ]
    }
