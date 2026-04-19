"""
Model training API.
"""
import threading
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.task import Task, TaskStatus, TaskType
from ..schemas.task import TaskResponse
from ..services.model_trainer import ModelTrainer
from ..services.model_utils import get_model_feature_importance

router = APIRouter(prefix="/api/model", tags=["模型训练"])

trainer = ModelTrainer()


def _to_native(obj):
    """Convert numpy values to plain Python values for JSON storage."""
    if isinstance(obj, dict):
        return {key: _to_native(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_to_native(value) for value in obj]
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if hasattr(obj, "item"):
        return obj.item()
    return obj


def run_training_task(
    task_id: int,
    model_type: str,
    test_size: float,
    tune_hyperparameters: bool,
    cross_validation: bool
):
    """Execute model training in a background thread."""
    from ..database import SessionLocal

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        return

    try:
        task.status = TaskStatus.RUNNING
        task.current_step = "正在加载训练数据..."
        task.progress = 10
        db.commit()

        if model_type == "all":
            task.current_step = "正在训练全部模型..."
            task.progress = 25
            db.commit()

            result = trainer.train_all_models(test_size=test_size)
            task.result_dict = {
                "models": list(result.keys()),
                "metrics": {
                    key: {
                        "train_r2": float(value["train_metrics"]["r2_score"]),
                        "test_r2": float(value["test_metrics"]["r2_score"]),
                        "test_rmse": float(value["test_metrics"]["rmse"]),
                        "test_mae": float(value["test_metrics"]["mae"]),
                        "version": value["version"],
                        "saved_at": value["saved_at"]
                    }
                    for key, value in result.items()
                },
                "test_ratio": float(test_size)
            }
        else:
            task.current_step = f"正在训练 {model_type.upper()} 模型..."
            task.progress = 30
            db.commit()

            result = trainer.train_model(
                model_type=model_type,
                test_size=test_size,
                tune_hyperparameters=tune_hyperparameters if model_type == "xgboost" else False,
                cross_validation=cross_validation if model_type == "xgboost" else False
            )

            task.result_dict = {
                "model_type": result["model_type"],
                "version": result["version"],
                "model_path": result["model_path"],
                "saved_at": result["saved_at"],
                "metrics": {
                    "train_r2": float(result["train_metrics"]["r2_score"]),
                    "test_r2": float(result["test_metrics"]["r2_score"]),
                    "test_rmse": float(result["test_metrics"]["rmse"]),
                    "test_mae": float(result["test_metrics"]["mae"])
                },
                "feature_importance": _to_native(result["feature_importance"]),
                "dataset_size": int(result["dataset_size"]),
                "train_size": int(result["train_size"]),
                "test_size": int(result["test_size"]),
                "test_ratio": float(result["test_ratio"])
            }

        task.status = TaskStatus.SUCCESS
        task.progress = 100
        task.current_step = "训练完成"
        db.commit()
    except Exception as exc:
        db.rollback()
        task.status = TaskStatus.FAILED
        task.current_step = "训练失败"
        task.error_msg = str(exc)
        db.commit()
    finally:
        db.close()


@router.post("/train")
async def start_training(
    model_type: str = Query(..., description="模型类型: lr, xgboost, transformer, all"),
    test_size: float = Query(0.3, description="测试集比例"),
    tune_hyperparameters: bool = Query(True, description="是否启用超参调优"),
    cross_validation: bool = Query(True, description="是否启用交叉验证"),
    db: Session = Depends(get_db)
):
    """Create a training task and launch the worker thread."""
    valid_types = ["lr", "xgboost", "transformer", "all"]
    if model_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的模型类型，支持: {', '.join(valid_types)}")

    if not 0.05 <= test_size <= 0.5:
        raise HTTPException(status_code=400, detail="测试集比例必须在 0.05 到 0.5 之间")

    running_task = db.query(Task).filter(
        Task.task_type == TaskType.TRAIN,
        Task.status == TaskStatus.RUNNING
    ).first()
    if running_task:
        raise HTTPException(status_code=400, detail="已有训练任务正在运行")

    task = Task(
        task_type=TaskType.TRAIN,
        status=TaskStatus.PENDING,
        current_step="准备训练数据",
        config_dict={
            "model_type": model_type,
            "test_size": test_size,
            "tune_hyperparameters": tune_hyperparameters,
            "cross_validation": cross_validation
        }
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=run_training_task,
        args=(
            task.id,
            model_type,
            test_size,
            tune_hyperparameters,
            cross_validation
        ),
        daemon=True
    )
    thread.start()

    return TaskResponse.model_validate(task.to_dict())


@router.get("/status", response_model=TaskResponse)
async def get_training_status(
    task_id: Optional[int] = Query(None, description="任务 ID"),
    db: Session = Depends(get_db)
):
    """Return status for a given task, or the latest training task."""
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
    """List all saved model files."""
    _ = db
    model_dir = Path(settings.MODEL_DIR)
    if not model_dir.exists():
        return {"models": []}

    model_files = []
    for file_path in model_dir.glob("*.pkl"):
        try:
            parts = file_path.stem.split("_", 1)
            current_model_type = parts[0]
            version = parts[1] if len(parts) > 1 else "unknown"
            model_files.append({
                "id": hash(str(file_path)) % (10 ** 8),
                "model_type": current_model_type,
                "version": version,
                "file_path": str(file_path),
                "is_active": True,
                "created_at": file_path.stat().st_mtime
            })
        except Exception:
            continue

    if model_type:
        model_files = [item for item in model_files if item["model_type"] == model_type]

    model_files.sort(key=lambda item: item["created_at"], reverse=True)
    return {"models": model_files}


@router.post("/select")
async def select_model(
    model_type: str = Query(..., description="模型类型: lr, xgboost"),
    db: Session = Depends(get_db)
):
    """Select an active model type."""
    _ = db
    valid_types = ["lr", "xgboost"]
    if model_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的模型类型，支持: {', '.join(valid_types)}")

    return {
        "message": f"已选择 {model_type.upper()} 模型",
        "model_type": model_type
    }


@router.get("/metrics/{model_type}")
async def get_model_metrics(
    model_type: str,
    db: Session = Depends(get_db)
):
    """Load metrics for the latest saved model of the given type."""
    _ = db
    model_dir = Path(settings.MODEL_DIR)
    model_files = list(model_dir.glob(f"{model_type}_*.pkl"))
    if not model_files:
        raise HTTPException(status_code=404, detail=f"未找到 {model_type} 模型")

    latest_model = max(model_files, key=lambda path: path.stat().st_mtime)

    try:
        model_data = joblib.load(latest_model)
        metrics = model_data.get("metrics", {})
        feature_importance = get_model_feature_importance(model_data)
        return {
            "model_type": model_type,
            "model_path": str(latest_model),
            "metrics": {
                "r2_score": metrics.get("r2_score", 0),
                "rmse": metrics.get("rmse", 0),
                "mae": metrics.get("mae", 0),
                "mape": metrics.get("mape", 0)
            },
            "feature_importance": feature_importance,
            "best_params": model_data.get("best_params", {})
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"加载模型指标失败: {exc}")
