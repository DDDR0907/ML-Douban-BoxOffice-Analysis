"""
Prediction API
预测接口 - 单个预测、批量预测、预测历史
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import pandas as pd
from io import BytesIO

from ..database import get_db
from ..models.movie import Movie
from ..models.prediction import Prediction, ModelType
from ..schemas.prediction import PredictionCreate, PredictionResponse, PredictionCompareResponse
from ..schemas.task import TaskResponse
from ..services.predictor import get_predictor, PredictionSaver

router = APIRouter(prefix="/api/predict", tags=["票房预测"])


@router.post("/single", response_model=PredictionResponse)
async def predict_single(
    movie_id: Optional[int] = Query(None, description="电影ID，如果提供则使用已有电影数据"),
    model_type: str = Query("xgboost", description="模型类型: lr, xgboost"),
    title: Optional[str] = Query(None, description="电影名称"),
    rating: Optional[float] = Query(None, description="豆瓣评分"),
    rating_count: Optional[int] = Query(None, description="评分人数"),
    wish_count: Optional[int] = Query(None, description="想看人数"),
    movie_type: Optional[str] = Query(None, description="电影类型"),
    release_year: Optional[int] = Query(None, description="上映年份"),
    avg_price: Optional[float] = Query(None, description="平均票价"),
    db: Session = Depends(get_db)
):
    """
    单部电影票房预测

    方式1：提供movie_id，使用数据库中的电影数据
    方式2：提供电影各项特征参数
    """
    # 验证模型类型
    if model_type not in ["lr", "xgboost"]:
        raise HTTPException(status_code=400, detail="无效的模型类型，支持: lr, xgboost")

    # 获取电影数据
    if movie_id:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="电影不存在")
    else:
        # 验证必需参数
        if not all([title, rating, rating_count]):
            raise HTTPException(
                status_code=400,
                detail="使用手动输入方式时，必须提供: title, rating, rating_count"
            )

        # 使用提供的参数创建临时电影对象
        movie = Movie(
            title=title,
            rating=rating,
            rating_count=rating_count,
            wish_count=wish_count or 0,
            type=movie_type,
            release_year=release_year,
            avg_price=avg_price
        )

    try:
        # 获取预测器并预测
        predictor = get_predictor(model_type)
        result = predictor.predict(movie, return_confidence=True)

        # 保存预测结果
        saver = PredictionSaver()
        prediction = saver.save_prediction(movie_id, result, model_type)
        saver.db.close()

        # 添加电影信息
        result['id'] = prediction.id
        result['movie_id'] = movie_id
        result['title'] = movie.title
        result['created_at'] = prediction.created_at.isoformat()

        # 如果有实际票房，计算误差
        if movie.box_office_wan:
            result['actual_box_office_wan'] = movie.box_office_wan
            result['error_wan'] = abs(result['predicted_box_office_wan'] - movie.box_office_wan)
            result['error_percentage'] = (result['error_wan'] / movie.box_office_wan * 100) if movie.box_office_wan > 0 else None

        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/batch")
async def predict_batch(
    file: UploadFile = File(...),
    model_type: str = Query("xgboost", description="模型类型"),
    db: Session = Depends(get_db)
):
    """
    批量预测（上传Excel文件）

    Excel文件应包含以下列（映射已存在的电影）：
    - title: 电影名称（用于查找数据库中的电影）
    或
    - id: 电影ID

    或者直接包含电影特征：
    - title, rating, rating_count, wish_count, type, release_year, avg_price
    """
    # 验证模型类型
    if model_type not in ["lr", "xgboost"]:
        raise HTTPException(status_code=400, detail="无效的模型类型")

    try:
        # 读取文件
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        if len(df) == 0:
            raise HTTPException(status_code=400, detail="文件为空")

        # 获取预测器
        predictor = get_predictor(model_type)

        results = []
        movies = []

        # 处理每一行
        for _, row in df.iterrows():
            movie = None

            # 尝试通过ID查找
            if 'id' in row and pd.notna(row['id']):
                movie = db.query(Movie).filter(Movie.id == int(row['id'])).first()

            # 尝试通过标题查找
            elif 'title' in row and pd.notna(row['title']):
                movie = db.query(Movie).filter(Movie.title == str(row['title'])).first()

            # 如果找到电影，进行预测
            if movie:
                try:
                    result = predictor.predict(movie, return_confidence=True)
                    result['movie_id'] = movie.id
                    result['title'] = movie.title

                    # 添加实际票房对比
                    if movie.box_office_wan:
                        result['actual_box_office_wan'] = movie.box_office_wan
                        result['error_wan'] = abs(result['predicted_box_office_wan'] - movie.box_office_wan)
                        result['error_percentage'] = (result['error_wan'] / movie.box_office_wan * 100) if movie.box_office_wan > 0 else None

                    results.append(result)
                    movies.append(movie)

                except Exception as e:
                    results.append({
                        'title': row.get('title', 'Unknown'),
                        'error': f"预测失败: {str(e)}"
                    })
            else:
                # 如果找不到电影，尝试用提供的特征创建临时电影
                if all(col in row for col in ['title', 'rating', 'rating_count']):
                    try:
                        movie = Movie(
                            title=row['title'],
                            rating=float(row['rating']) if pd.notna(row['rating']) else None,
                            rating_count=int(row['rating_count']) if pd.notna(row['rating_count']) else None,
                            wish_count=int(row['wish_count']) if 'wish_count' in row and pd.notna(row['wish_count']) else 0,
                            type=row.get('type'),
                            release_year=int(row['release_year']) if 'release_year' in row and pd.notna(row['release_year']) else None,
                            avg_price=float(row['avg_price']) if 'avg_price' in row and pd.notna(row['avg_price']) else None
                        )

                        result = predictor.predict(movie, return_confidence=True)
                        result['movie_id'] = None
                        result['title'] = movie.title
                        results.append(result)

                    except Exception as e:
                        results.append({
                            'title': row.get('title', 'Unknown'),
                            'error': f"预测失败: {str(e)}"
                        })
                else:
                    results.append({
                        'title': row.get('title', 'Unknown'),
                        'error': '未找到电影且缺少必要特征'
                    })

        # 保存预测结果
        saver = PredictionSaver()
        try:
            saved = saver.save_batch_predictions(results, model_type)
            saver.db.close()
        except Exception as e:
            print(f"保存预测结果时出错: {e}")

        return {
            "message": f"批量预测完成",
            "total": len(results),
            "success": sum(1 for r in results if 'error' not in r),
            "failed": sum(1 for r in results if 'error' in r),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量预测失败: {str(e)}")


@router.get("/history")
async def get_prediction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    movie_id: Optional[int] = Query(None, description="筛选电影ID"),
    model_type: Optional[str] = Query(None, description="筛选模型类型"),
    db: Session = Depends(get_db)
):
    """
    获取预测历史记录
    """
    from sqlalchemy.orm import selectinload

    query = db.query(Prediction).options(selectinload(Prediction.movie))

    # 筛选
    if movie_id:
        query = query.filter(Prediction.movie_id == movie_id)
    if model_type:
        query = query.filter(Prediction.model_type == model_type)

    total = query.count()

    offset = (page - 1) * page_size
    predictions = query.order_by(Prediction.id.desc()).offset(offset).limit(page_size).all()

    result_data = []
    for p in predictions:
        pred_dict = p.to_dict()
        if p.movie:
            pred_dict['movie'] = {"id": p.movie.id, "title": p.movie.title}
        result_data.append(pred_dict)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": result_data
    }


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个预测详情
    """
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="预测记录不存在")

    return PredictionResponse.model_validate(prediction.to_dict())


@router.get("/compare/{movie_id}")
async def compare_predictions(
    movie_id: int,
    db: Session = Depends(get_db)
):
    """
    对比同一部电影的多个模型预测结果
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    # 获取已有预测记录
    predictions = db.query(Prediction).filter(Prediction.movie_id == movie_id).all()

    result = {
        "movie_id": movie_id,
        "movie_title": movie.title,
        "actual_box_office": movie.box_office,
        "actual_box_office_wan": movie.box_office_wan,
        "predictions": {}
    }

    # 添加已有预测
    for pred in predictions:
        result["predictions"][pred.model_type.value] = {
            "predicted_box_office": pred.predicted_box_office,
            "predicted_box_office_wan": pred.predicted_box_office_wan,
            "confidence_lower": pred.confidence_lower,
            "confidence_upper": pred.confidence_upper,
            "created_at": pred.created_at.isoformat()
        }

    # 尝试使用所有模型进行实时预测对比
    try:
        predictor = get_predictor('xgboost')
        comparison = predictor.compare_models(movie)

        for model_type, pred_result in comparison.items():
            if 'error' not in model_type:
                result["predictions"][model_type] = {
                    "predicted_box_office": pred_result.get('predicted_box_office'),
                    "predicted_box_office_wan": pred_result.get('predicted_box_office_wan'),
                    "confidence_lower": pred_result.get('confidence_lower'),
                    "confidence_upper": pred_result.get('confidence_upper'),
                    "feature_importance": pred_result.get('feature_importance', {})
                }

    except Exception as e:
        result["prediction_error"] = str(e)

    return result
