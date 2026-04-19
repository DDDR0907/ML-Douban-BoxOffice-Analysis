"""
Visualization API
Provide chart data for the frontend visualization pages.
"""
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.movie import Movie
from ..services.feature_engineering import FeatureEngineering
from ..services.model_utils import get_model_feature_importance

router = APIRouter(prefix="/api/visualize", tags=["数据可视化"])

MODEL_LABELS = {
    "xgboost": "XGBoost",
    "lr": "线性回归"
}


def _load_latest_model_data(model_type: str) -> Optional[Dict]:
    """Load the newest saved model payload for the requested model type."""
    model_dir = Path(settings.MODEL_DIR)
    if not model_dir.exists():
        return None

    model_files = list(model_dir.glob(f"{model_type}_*.pkl"))
    if not model_files:
        return None

    latest_model = max(model_files, key=lambda path: path.stat().st_mtime)
    return joblib.load(latest_model)


def _load_model_importance(model_type: str) -> Dict[str, float]:
    """Return normalized feature importance for a saved model."""
    model_data = _load_latest_model_data(model_type)
    if not model_data:
        return {}
    return get_model_feature_importance(model_data)


@router.get("/rating-boxoffice")
async def rating_boxoffice_scatter(
    db: Session = Depends(get_db)
):
    """评分 - 票房散点图数据。"""
    movies = db.query(Movie).filter(
        Movie.rating.isnot(None),
        Movie.box_office_wan.isnot(None)
    ).limit(500).all()

    data = [
        {
            "x": movie.rating,
            "y": movie.box_office_wan,
            "title": movie.title,
            "type": movie.type,
            "year": movie.release_year
        }
        for movie in movies
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
    """不同类型电影票房分布箱线图数据。"""
    movies = db.query(Movie).filter(
        Movie.type.isnot(None),
        Movie.box_office_wan.isnot(None)
    ).all()

    genre_data = {}
    for movie in movies:
        if movie.type:
            genre_data.setdefault(movie.type, []).append(movie.box_office_wan)

    data = [
        {
            "type": genre,
            "values": values,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "median": sorted(values)[len(values) // 2] if values else 0,
            "q1": sorted(values)[len(values) // 4] if len(values) > 4 else 0,
            "q3": sorted(values)[len(values) * 3 // 4] if len(values) > 4 else 0,
        }
        for genre, values in genre_data.items()
        if len(values) >= 5
    ]

    data.sort(key=lambda item: item["median"], reverse=True)

    return {
        "chart_type": "boxplot",
        "x_axis": "电影类型",
        "y_axis": "票房（万元）",
        "data": data[:10]
    }


@router.get("/model-comparison")
async def model_performance_comparison(
    db: Session = Depends(get_db)
):
    """模型性能对比图数据。"""
    _ = db
    models = {}

    for model_type in ["lr", "xgboost"]:
        try:
            model_data = _load_latest_model_data(model_type)
            if not model_data:
                continue

            test_metrics = model_data.get("test_metrics", model_data.get("metrics", {}))
            models[MODEL_LABELS.get(model_type, model_type)] = {
                "R2": round(test_metrics.get("r2_score", 0), 4),
                "RMSE": round(test_metrics.get("rmse", 0), 2),
                "MAE": round(test_metrics.get("mae", 0), 2)
            }
        except Exception as exc:
            print(f"加载模型 {model_type} 失败: {exc}")

    return {
        "chart_type": "bar",
        "metrics": ["R2", "RMSE", "MAE"],
        "models": models
    }


@router.get("/feature-importance")
async def feature_importance(
    model_type: str = Query("xgboost", description="模型类型"),
    db: Session = Depends(get_db)
):
    """单模型特征重要性数据。"""
    _ = db
    importance_dict = _load_model_importance(model_type)

    if not importance_dict:
        return {
            "model_type": model_type,
            "chart_type": "horizontal_bar",
            "data": [],
            "message": f"未找到 {MODEL_LABELS.get(model_type, model_type)} 模型特征重要性数据"
        }

    data = [
        {
            "feature": feature,
            "importance": round(value * 100, 2)
        }
        for feature, value in importance_dict.items()
    ]

    return {
        "model_type": model_type,
        "chart_type": "horizontal_bar",
        "data": data[:15]
    }


@router.get("/feature-correlation-heatmap")
async def feature_correlation_heatmap(
    limit: int = Query(12, ge=4, le=20, description="除票房外最多展示的数值特征数量"),
    db: Session = Depends(get_db)
):
    """数值特征与票房的相关性热力图数据。"""
    movies = db.query(Movie).filter(Movie.box_office_wan.isnot(None)).all()

    if not movies:
        return {
            "chart_type": "heatmap",
            "features": [],
            "matrix": [],
            "message": "暂无可用于相关性分析的数据"
        }

    df = pd.DataFrame([movie.to_dict() for movie in movies])
    feature_engineering = FeatureEngineering()
    df = feature_engineering.create_derived_features(df)

    exclude_cols = {"id", "box_office"}
    numeric_cols = [
        column for column in df.select_dtypes(include=[np.number]).columns
        if column not in exclude_cols
    ]

    if "box_office_wan" not in numeric_cols:
        return {
            "chart_type": "heatmap",
            "features": [],
            "matrix": [],
            "message": "缺少票房数值字段，无法计算相关性"
        }

    corr_matrix = df[numeric_cols].corr().fillna(0)
    if "box_office_wan" not in corr_matrix.columns:
        return {
            "chart_type": "heatmap",
            "features": [],
            "matrix": [],
            "message": "无法计算票房相关性"
        }

    corr_with_target = corr_matrix["box_office_wan"].drop(labels=["box_office_wan"], errors="ignore")
    top_features = corr_with_target.abs().sort_values(ascending=False).head(limit).index.tolist()
    heatmap_features = top_features + ["box_office_wan"]
    heatmap_matrix = corr_matrix.loc[heatmap_features, heatmap_features].round(4)

    return {
        "chart_type": "heatmap",
        "target": "box_office_wan",
        "features": heatmap_features,
        "feature_labels": {
            "box_office_wan": "票房（万元）"
        },
        "matrix": heatmap_matrix.values.tolist(),
        "correlations": [
            {
                "feature": feature,
                "correlation": round(float(corr_with_target[feature]), 4)
            }
            for feature in top_features
        ]
    }


@router.get("/multi-model-feature-importance")
async def multi_model_feature_importance(
    limit: int = Query(10, ge=5, le=20, description="展示的特征数量"),
    db: Session = Depends(get_db)
):
    """多模型特征重要性对比数据。"""
    _ = db
    model_importance_map = {}

    for model_type in ["xgboost", "lr"]:
        importance = _load_model_importance(model_type)
        if importance:
            model_importance_map[model_type] = importance

    if not model_importance_map:
        return {
            "chart_type": "grouped_bar",
            "features": [],
            "models": [],
            "message": "暂无已训练模型的特征重要性数据"
        }

    feature_scores = {}
    for importance in model_importance_map.values():
        for feature, value in importance.items():
            feature_scores[feature] = feature_scores.get(feature, 0.0) + value

    selected_features = [
        feature for feature, _ in sorted(
            feature_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )[:limit]
    ]

    models = []
    for model_type, importance in model_importance_map.items():
        models.append({
            "model_type": model_type,
            "model_name": MODEL_LABELS.get(model_type, model_type),
            "values": [
                round(float(importance.get(feature, 0.0)) * 100, 2)
                for feature in selected_features
            ]
        })

    return {
        "chart_type": "grouped_bar",
        "features": selected_features,
        "models": models
    }


@router.get("/predict-comparison")
async def predict_vs_actual(
    movie_id: Optional[int] = Query(None, description="指定电影ID"),
    limit: int = Query(20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """预测 vs 实际票房对比图数据。"""
    from ..models.prediction import Prediction

    query = db.query(Prediction).filter(
        Prediction.movie_id.isnot(None),
        Prediction.predicted_box_office.isnot(None)
    )

    if movie_id:
        query = query.filter(Prediction.movie_id == movie_id)

    predictions = query.order_by(Prediction.id.desc()).limit(limit).all()

    data = []
    for prediction in predictions:
        if prediction.movie:
            data.append({
                "title": prediction.movie.title,
                "actual": prediction.movie.box_office_wan,
                "predicted": prediction.predicted_box_office_wan,
                "model_type": prediction.model_type.value
            })

    return {
        "chart_type": "line",
        "data": data
    }


@router.get("/year-trend")
async def boxoffice_year_trend(
    db: Session = Depends(get_db)
):
    """年度票房趋势图数据。"""
    from sqlalchemy import func

    results = db.query(
        Movie.release_year,
        func.sum(Movie.box_office_wan).label("total_box_office"),
        func.count(Movie.id).label("movie_count"),
        func.avg(Movie.rating).label("avg_rating")
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
    """Top 电影榜单数据。"""
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
            "rank": index + 1,
            "title": movie.title,
            "box_office": movie.box_office_wan,
            "rating": movie.rating,
            "year": movie.release_year,
            "type": movie.type
        }
        for index, movie in enumerate(movies)
    ]

    return {
        "by": by,
        "data": data
    }


@router.get("/data-overview")
async def data_overview(
    db: Session = Depends(get_db)
):
    """数据概览统计。"""
    from sqlalchemy import func
    from ..models.prediction import Prediction

    total_movies = db.query(func.count(Movie.id)).scalar()
    movies_with_box_office = db.query(func.count(Movie.id)).filter(
        Movie.box_office_wan.isnot(None)
    ).scalar()
    movies_with_rating = db.query(func.count(Movie.id)).filter(
        Movie.rating.isnot(None)
    ).scalar()

    box_office_stats = db.query(
        func.min(Movie.box_office_wan).label("min"),
        func.max(Movie.box_office_wan).label("max"),
        func.avg(Movie.box_office_wan).label("avg")
    ).filter(
        Movie.box_office_wan.isnot(None)
    ).first()

    rating_stats = db.query(
        func.min(Movie.rating).label("min"),
        func.max(Movie.rating).label("max"),
        func.avg(Movie.rating).label("avg")
    ).filter(
        Movie.rating.isnot(None)
    ).first()

    total_predictions = db.query(func.count(Prediction.id)).scalar()

    data_source_stats = db.query(
        Movie.data_source,
        func.count(Movie.id).label("count")
    ).group_by(
        Movie.data_source
    ).all()

    year_distribution = db.query(
        Movie.release_year,
        func.count(Movie.id).label("count")
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
