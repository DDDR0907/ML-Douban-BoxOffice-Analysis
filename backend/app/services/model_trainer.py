"""
Model Training Module
模型训练模块 - 线性回归、XGBoost、Transformer
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import xgboost as xgb
import joblib
from pathlib import Path
from datetime import datetime

from ..config import settings
from ..database import SessionLocal
from ..models.movie import Movie
from .feature_engineering import FeatureEngineering, FeaturePipeline
from .model_utils import normalize_feature_importance


class LinearRegressionModel:
    """线性回归模型"""

    def __init__(self):
        self.model = LinearRegression()
        self.feature_names = None
        self.metrics = {}

    def train(self, X_train: np.ndarray, y_train: np.ndarray, feature_names: List[str] = None):
        """训练模型"""
        self.model.fit(X_train, y_train)
        self.feature_names = feature_names or []

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        return self.model.predict(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """评估模型"""
        y_pred = self.predict(X_test)

        self.metrics = {
            'r2_score': r2_score(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100 if y_test.all() else None
        }

        return self.metrics

    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性（使用系数）"""
        if self.feature_names and hasattr(self.model, 'coef_'):
            importance = dict(zip(self.feature_names, np.abs(self.model.coef_)))
            # 归一化
            total = sum(importance.values())
            if total > 0:
                importance = {k: v/total for k, v in importance.items()}
            return importance
        return {}

    def save(self, path: str):
        """保存模型"""
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'metrics': self.metrics
        }, path)

    def load(self, path: str):
        """加载模型"""
        data = joblib.load(path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        self.metrics = data['metrics']


class XGBoostModel:
    """XGBoost回归模型"""

    def __init__(self):
        self.model = None
        self.feature_names = None
        self.metrics = {}
        self.best_params = {}

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: List[str] = None,
        tune_hyperparameters: bool = True
    ):
        """训练模型"""
        self.feature_names = feature_names or []

        if tune_hyperparameters:
            # 网格搜索调参
            param_grid = {
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.2],
                'n_estimators': [100, 200, 300],
                'subsample': [0.8, 1.0],
            }

            self.model = xgb.XGBRegressor(
                objective='reg:squarederror',
                random_state=42
            )

            grid_search = GridSearchCV(
                self.model,
                param_grid,
                cv=5,
                scoring='r2',
                n_jobs=-1,
                verbose=0
            )

            grid_search.fit(X_train, y_train)
            self.model = grid_search.best_estimator_
            self.best_params = grid_search.best_params_
        else:
            # 使用默认参数
            self.model = xgb.XGBRegressor(
                max_depth=5,
                learning_rate=0.1,
                n_estimators=200,
                objective='reg:squarederror',
                random_state=42
            )
            self.model.fit(X_train, y_train)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        return self.model.predict(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """评估模型"""
        y_pred = self.predict(X_test)

        self.metrics = {
            'r2_score': r2_score(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100 if y_test.all() else None
        }

        return self.metrics

    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if self.feature_names and hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
            # 归一化
            total = sum(importance.values())
            if total > 0:
                importance = {k: v/total for k, v in importance.items()}
            # 按重要性排序
            return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return {}

    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv: int = 5) -> Dict[str, Any]:
        """交叉验证"""
        scores = cross_val_score(
            self.model, X, y,
            cv=cv,
            scoring='r2',
            n_jobs=-1
        )

        return {
            'mean_r2': scores.mean(),
            'std_r2': scores.std(),
            'scores': scores.tolist()
        }

    def save(self, path: str):
        """保存模型"""
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'best_params': self.best_params
        }, path)

    def load(self, path: str):
        """加载模型"""
        data = joblib.load(path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        self.metrics = data['metrics']
        self.best_params = data.get('best_params', {})


class ModelTrainer:
    """模型训练管理器"""

    def __init__(self):
        self.fe = FeatureEngineering()
        self.feature_pipeline = None  # 特征工程管道
        self.models = {
            'lr': LinearRegressionModel(),
            'xgboost': XGBoostModel(),
        }
        self.model_dir = Path(settings.MODEL_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def load_data_from_db(self, limit: int = None) -> pd.DataFrame:
        """从数据库加载数据"""
        db = SessionLocal()
        query = db.query(Movie).filter(
            Movie.box_office_wan.isnot(None)
        )

        if limit:
            query = query.limit(limit)

        movies = query.all()
        db.close()

        # 转换为DataFrame
        data = [m.to_dict() for m in movies]
        df = pd.DataFrame(data)

        print(f"从数据库加载 {len(df)} 条电影数据")

        return df

    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str = 'box_office_wan',
        test_size: float = 0.3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """
        准备训练数据

        Returns:
            X_train, X_test, y_train, y_test, feature_names
        """
        # 特征工程
        df_processed, features = self.fe.prepare_features_for_model(
            df,
            target_col=target_col,
            feature_selection=True,
            create_derived=True,
            handle_missing=True,
            normalize=True
        )

        # 分割数据集
        X = df_processed[features].values
        y = df_processed[target_col].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        print(f"\n数据集分割:")
        print(f"  训练集: {len(X_train)} 样本")
        print(f"  测试集: {len(X_test)} 样本")

        return X_train, X_test, y_train, y_test, features

    def train_model(
        self,
        model_type: str = 'xgboost',
        test_size: float = 0.3,
        tune_hyperparameters: bool = True,
        cross_validation: bool = True
    ) -> Dict[str, Any]:
        """
        训练模型

        Args:
            model_type: 模型类型 ('lr' 或 'xgboost')
            tune_hyperparameters: 是否调参
            cross_validation: 是否交叉验证

        Returns:
            训练结果
        """
        print(f"\n{'='*60}")
        print(f"开始训练 {model_type.upper()} 模型")
        print(f"{'='*60}")

        # 加载数据
        df = self.load_data_from_db()

        if len(df) < 100:
            print(f"警告: 数据量较少 ({len(df)} 条)，建议至少100条数据")

        # 使用特征工程管道
        print("\n创建并训练特征工程管道...")
        self.feature_pipeline = FeaturePipeline()
        X = self.feature_pipeline.fit_transform(df, target_col='box_office_wan')
        y = df['box_office_wan'].values

        # 分割数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        print(f"\n数据集分割:")
        print(f"  训练集: {len(X_train)} 样本")
        print(f"  测试集: {len(X_test)} 样本")
        print(f"  特征数: {X_train.shape[1]}")

        # 训练模型
        model = self.models[model_type]

        if model_type == 'xgboost':
            model.train(X_train, y_train, self.feature_pipeline.final_features, tune_hyperparameters=tune_hyperparameters)
        else:
            model.train(X_train, y_train, self.feature_pipeline.final_features)

        # 评估模型
        train_metrics = model.evaluate(X_train, y_train)
        test_metrics = model.evaluate(X_test, y_test)

        print(f"\n{'='*60}")
        print(f"模型评估结果 ({model_type.upper()})")
        print(f"{'='*60}")
        print(f"\n训练集:")
        for k, v in train_metrics.items():
            print(f"  {k}: {v:.4f}")

        print(f"\n测试集:")
        for k, v in test_metrics.items():
            print(f"  {k}: {v:.4f}")

        # 交叉验证
        cv_results = {}
        if cross_validation and model_type == 'xgboost':
            print(f"\n执行5折交叉验证...")
            cv_results = model.cross_validate(X_train, y_train, cv=5)
            print(f"  交叉验证 R²: {cv_results['mean_r2']:.4f} ± {cv_results['std_r2']:.4f}")

        # 特征重要性
        feature_importance = model.get_feature_importance()
        feature_importance = normalize_feature_importance(feature_importance)
        print(f"\n特征重要性:")
        for feat, imp in list(feature_importance.items())[:10]:
            print(f"  {feat}: {imp:.2%}")

        # 保存模型（包含特征工程管道）
        version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model_path = self.model_dir / f"{model_type}_{version}.pkl"

        joblib.dump({
            'model': model.model,
            'feature_names': self.feature_pipeline.final_features,
            'metrics': test_metrics,
            'best_params': model.best_params if model_type == 'xgboost' else {},
            'feature_importance': feature_importance,
            'feature_pipeline': {
                'scaler': self.feature_pipeline.scaler,
                'label_encoders': self.feature_pipeline.label_encoders,
                'fill_strategies': self.feature_pipeline.fill_strategies,
                'final_features': self.feature_pipeline.final_features
            }
        }, str(model_path))

        print(f"\n模型已保存: {model_path}")
        print(f"特征工程管道已包含在模型中")

        return {
            'model_type': model_type,
            'version': version,
            'model_path': str(model_path),
            'saved_at': datetime.now().isoformat(),
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'cv_results': cv_results,
            'feature_importance': feature_importance,
            'feature_names': self.feature_pipeline.final_features,
            'dataset_size': int(len(df)),
            'train_size': int(len(X_train)),
            'test_size': int(len(X_test)),
            'test_ratio': float(test_size)
        }

    def train_all_models(self, test_size: float = 0.3) -> Dict[str, Any]:
        """训练所有模型并对比"""
        results = {}

        # 训练线性回归
        results['lr'] = self.train_model(
            'lr',
            test_size=test_size,
            tune_hyperparameters=False,
            cross_validation=False
        )

        # 训练XGBoost
        results['xgboost'] = self.train_model(
            'xgboost',
            test_size=test_size,
            tune_hyperparameters=True,
            cross_validation=True
        )

        # 模型对比
        print(f"\n{'='*60}")
        print("模型性能对比")
        print(f"{'='*60}")
        print(f"\n{'模型':<15} {'训练R²':<12} {'测试R²':<12} {'测试RMSE':<15} {'测试MAE':<12}")
        print("-" * 70)

        for model_type, result in results.items():
            train_r2 = result['train_metrics']['r2_score']
            test_r2 = result['test_metrics']['r2_score']
            test_rmse = result['test_metrics']['rmse']
            test_mae = result['test_metrics']['mae']

            print(f"{model_type.upper():<15} {train_r2:<12.4f} {test_r2:<12.4f} {test_rmse:<15.2f} {test_mae:<12.2f}")

        # 计算改进百分比
        baseline_rmse = results['lr']['test_metrics']['rmse']
        xgb_rmse = results['xgboost']['test_metrics']['rmse']
        improvement = (baseline_rmse - xgb_rmse) / baseline_rmse * 100

        print(f"\nXGBoost 相比线性回归 RMSE 降低: {improvement:.2f}%")

        return results


# 全局训练器实例
model_trainer = ModelTrainer()


def quick_test():
    """快速测试模型训练"""
    print("开始快速测试...")

    # 使用已有的数据
    trainer = ModelTrainer()

    # 只训练一个XGBoost模型进行测试
    result = trainer.train_model(
        model_type='xgboost',
        tune_hyperparameters=False,  # 跳过网格搜索以加快速度
        cross_validation=False
    )

    print("\n测试完成!")
    return result


if __name__ == "__main__":
    quick_test()
