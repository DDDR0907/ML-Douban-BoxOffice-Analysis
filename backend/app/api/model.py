"""
Model Training API
模型训练接口 - 启动训练、查询状态、模型管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import threading
import numpy as np

from ..database import get_db
from ..models.task import Task, TaskType, TaskStatus
from ..schemas.task import TaskResponse
from ..services.model_trainer import ModelTrainer
from ..services.model_utils import get_model_feature_importance

router = APIRouter(prefix="/api/model", tags=["模型训练"])

# 全局训练器
trainer = ModelTrainer()


def run_training_task(task_id: int, model_type: str, test_size: float, db_url: str):
    """
    在后台线程中运行训练任务

    Args:
        task_id: 任务ID
        model_type: 模型类型
        test_size: 测试集比例
        db_url: 数据库URL
    """
    from ..database import SessionLocal
    from ..models.task import Task

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        return

    try:
        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.current_step = "正在加载数据..."
        task.progress = 10
        db.commit()

        # 训练模型
        if model_type == "all":
            task.current_step = "训练所有模型..."
            task.progress = 20
            db.commit()

            result = trainer.train_all_models()

            # 更新结果 - 转换numpy类型为Python原生类型
            task.result_dict = {
                "models": list(result.keys()),
                "metrics": {
                    k: {
                        "train_r2": float(v["train_metrics"]["r2_score"]),
                        "test_r2": float(v["test_metrics"]["r2_score"]),
                        "test_rmse": float(v["test_metrics"]["rmse"])
                    }
                    for k, v in result.items()
                }
            }
        else:
            task.current_step = f"训练 {model_type.upper()} 模型..."
            task.progress = 30
            db.commit()

            result = trainer.train_model(
                model_type=model_type,
                tune_hyperparameters=(model_type == "xgboost"),
                cross_validation=(model_type == "xgboost")
            )

            # 更新结果 - 转换numpy类型为Python原生类型
            def convert_to_native(obj):
                """递归转换numpy类型为Python原生类型"""
                if isinstance(obj, dict):
                    return {k: convert_to_native(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_native(v) for v in obj]
                elif isinstance(obj, (np.integer, np.floating)):
                    return float(obj)
                elif hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                else:
                    return obj

            task.result_dict = {
                "model_type": result["model_type"],
                "version": result["version"],
                "metrics": {
                    "train_r2": float(result["train_metrics"]["r2_score"]),
                    "test_r2": float(result["test_metrics"]["r2_score"]),
                    "test_rmse": float(result["test_metrics"]["rmse"]),
                    "test_mae": float(result["test_metrics"]["mae"])
                },
                "feature_importance": convert_to_native(result["feature_importance"])
            }

        # 任务完成
        task.status = TaskStatus.SUCCESS
        task.progress = 100
        task.current_step = "训练完成"
        db.commit()

    except Exception as e:
        db.rollback()
        task.status = TaskStatus.FAILED
        task.error_msg = str(e)
        task.current_step = "训练失败"
        db.commit()

    finally:
        db.close()


@router.post("/train")
async def start_training(
    background_tasks: BackgroundTasks,
    model_type: str = Query(..., description="模型类型: lr, xgboost, transformer, all"),
    test_size: float = Query(0.3, description="测试集比例"),
    db: Session = Depends(get_db)
):
    """
    开始训练模型

    参数：
    - model_type: 模型类型
      - lr: 线性回归
      - xgboost: XGBoost
      - transformer: Transformer
      - all: 训练所有模型
    - test_size: 测试集比例（默认0.3）
    """
    # 验证模型类型
    valid_types = ["lr", "xgboost", "transformer", "all"]
    if model_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的模型类型。支持: {', '.join(valid_types)}")

    # 检查是否有正在运行的训练任务
    running_task = db.query(Task).filter(
        Task.task_type == TaskType.TRAIN,
        Task.status == TaskStatus.RUNNING
    ).first()

    if running_task:
        raise HTTPException(status_code=400, detail="已有训练任务正在运行")

    # 创建训练任务
    task = Task(
        task_type=TaskType.TRAIN,
        status=TaskStatus.PENDING,
        current_step="准备训练数据",
        config_dict={
            "model_type": model_type,
            "test_size": test_size
        }
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 启动后台训练任务
    from ..config import settings
    thread = threading.Thread(
        target=run_training_task,
        args=(task.id, model_type, test_size, settings.DATABASE_URL)
    )
    thread.daemon = True
    thread.start()

    return TaskResponse.model_validate(task.to_dict())


@router.get("/status", response_model=TaskResponse)
async def get_training_status(
    task_id: Optional[int] = Query(None, description="任务ID"),
    db: Session = Depends(get_db)
):
    """
    获取训练任务状态
    """
    query = db.query(Task).filter(Task.task_type == TaskType.TRAIN)

    if task_id:
        query = query.filter(Task.id == task_id)
    else:
        query = query.order_by(Task.id.desc())

    task = query.first()

    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")

    return TaskResponse.model_validate(task.to_dict())


@router.get("/list")
async def list_models(
    model_type: Optional[str] = Query(None, description="筛选模型类型"),
    db: Session = Depends(get_db)
):
    """
    获取已训练的模型列表
    """
    from ..config import settings
    from pathlib import Path
    import os

    model_dir = Path(settings.MODEL_DIR)

    if not model_dir.exists():
        return {"models": []}

    # 查找所有模型文件
    model_files = []
    for file_path in model_dir.glob("*.pkl"):
        try:
            # 解析文件名获取模型信息
            parts = file_path.stem.split("_")
            if len(parts) >= 2:
                m_type = parts[0]
                version = "_".join(parts[1:]) if len(parts) > 2 else "1.0"

                # 获取文件修改时间
                mtime = os.path.getmtime(file_path)

                model_files.append({
                    "id": hash(str(file_path)) % (10**8),  # 简单ID生成
                    "model_type": m_type,
                    "version": version,
                    "file_path": str(file_path),
                    "is_active": True,  # 所有模型都是可用的
                    "created_at": mtime
                })
        except Exception:
            continue

    # 按类型筛选
    if model_type:
        model_files = [m for m in model_files if m["model_type"] == model_type]

    # 按创建时间排序
    model_files.sort(key=lambda x: x["created_at"], reverse=True)

    return {"models": model_files}


@router.post("/select")
async def select_model(
    model_type: str = Query(..., description="模型类型: lr, xgboost"),
    db: Session = Depends(get_db)
):
    """
    选择启用的模型类型
    """
    valid_types = ["lr", "xgboost"]
    if model_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的模型类型。支持: {', '.join(valid_types)}")

    # 这里可以保存到配置或数据库
    # 目前简单返回成功
    return {
        "message": f"已选择 {model_type.upper()} 模型",
        "model_type": model_type
    }


@router.get("/metrics/{model_type}")
async def get_model_metrics(
    model_type: str,
    db: Session = Depends(get_db)
):
    """
    获取模型评估指标
    """
    from ..config import settings
    from pathlib import Path
    import joblib

    model_dir = Path(settings.MODEL_DIR)

    # 查找该类型的最新模型
    model_files = list(model_dir.glob(f"{model_type}_*.pkl"))

    if not model_files:
        raise HTTPException(status_code=404, detail=f"未找到 {model_type} 模型")

    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)

    try:
        model_data = joblib.load(latest_model)
        metrics = model_data.get('metrics', {})
        feature_importance = get_model_feature_importance(model_data)

        return {
            "model_type": model_type,
            "metrics": {
                "r2_score": metrics.get('r2_score', 0),
                "rmse": metrics.get('rmse', 0),
                "mae": metrics.get('mae', 0),
                "mape": metrics.get('mape', 0)
            },
            "feature_importance": feature_importance,
            "best_params": model_data.get('best_params', {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载模型指标失败: {str(e)}")
