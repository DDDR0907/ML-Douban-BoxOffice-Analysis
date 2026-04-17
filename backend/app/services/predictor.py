"""
Predictor Service
预测服务 - 使用训练好的模型进行票房预测
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import joblib
import json

from ..config import settings
from ..database import SessionLocal
from ..models.movie import Movie
from ..models.prediction import Prediction, ModelType
from .feature_engineering import FeatureEngineering, FeaturePipeline


class Predictor:
    """
    票房预测器
    支持使用不同模型进行预测
    """

    def __init__(self, model_type: str = 'xgboost'):
        """
        初始化预测器

        Args:
            model_type: 模型类型 ('lr', 'xgboost')
        """
        self.model_type = model_type
        self.model = None
        self.feature_names = None
        self.scaler = None
        self.fe = FeatureEngineering()
        self.feature_pipeline = None  # 特征工程管道

        # 模型目录
        self.model_dir = Path(settings.MODEL_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 加载模型
        self._load_model()

    def _load_model(self):
        """加载模型和特征工程管道"""
        # 查找最新的模型文件
        model_files = list(self.model_dir.glob(f"{self.model_type}_*.pkl"))

        if not model_files:
            raise FileNotFoundError(
                f"未找到 {self.model_type} 模型文件。"
                f"请先训练模型或检查 {self.model_dir} 目录"
            )

        # 按修改时间排序，获取最新的模型
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)

        try:
            model_data = joblib.load(latest_model)
            self.model = model_data['model']
            self.feature_names = model_data.get('feature_names', [])
            self.scaler = model_data.get('scaler')

            # 加载特征工程管道
            if 'feature_pipeline' in model_data:
                self.feature_pipeline = FeaturePipeline()
                fp_data = model_data['feature_pipeline']
                self.feature_pipeline.scaler = fp_data.get('scaler')
                self.feature_pipeline.label_encoders = fp_data.get('label_encoders', {})
                self.feature_pipeline.fill_strategies = fp_data.get('fill_strategies', {})
                self.feature_pipeline.final_features = fp_data.get('final_features', [])
                print(f"成功加载特征工程管道，特征数量: {len(self.feature_pipeline.final_features)}")
            else:
                print(f"警告: 模型不包含特征工程管道，使用旧版特征工程")

            print(f"成功加载模型: {latest_model.name}")
            print(f"特征数量: {len(self.feature_names)}")

        except Exception as e:
            raise RuntimeError(f"加载模型失败: {e}")

    def _extract_features(self, movie: Movie) -> Dict[str, Any]:
        """
        从电影对象提取所有特征

        Args:
            movie: Movie对象

        Returns:
            特征字典
        """
        return {
            'title': movie.title,
            'type': movie.type,
            'release_year': movie.release_year,
            'rating': movie.rating,
            'rating_count': movie.rating_count,
            'wish_count': movie.wish_count,
            'avg_price': movie.avg_price,
            'box_office_wan': movie.box_office_wan,  # 用于特征工程
            # 添加模型需要的其他特征
            'ranking': movie.ranking,
            'per_session_attendance': movie.per_session_attendance,
            'created_at': movie.created_at,
            'updated_at': movie.updated_at,
        }

    def _prepare_features(
        self,
        movie_data: Dict[str, Any],
        fit_scaler: bool = False
    ) -> np.ndarray:
        """
        使用特征工程管道准备预测特征

        Args:
            movie_data: 电影数据字典
            fit_scaler: 是否重新拟合scaler（已废弃，保留用于兼容）

        Returns:
            特征数组
        """
        # 创建DataFrame
        df = pd.DataFrame([movie_data])

        # 使用特征工程管道
        if self.feature_pipeline is not None:
            return self.feature_pipeline.transform(df)
        else:
            # 回退到旧版特征工程
            print("警告: 特征工程管道未加载，使用旧版特征工程")

            # 应用特征工程
            df_processed = self.fe.create_derived_features(df)

            # 编码分类特征
            if 'type' in df_processed.columns:
                type_map = {
                    '剧情': 1, '喜剧': 2, '动作': 3, '爱情': 4, '科幻': 5,
                    '动画': 6, '悬疑': 7, '犯罪': 8, '战争': 9, '恐怖': 10,
                    '纪录片': 11, '传记': 12, '冒险': 13, '奇幻': 14,
                    '家庭': 15, '音乐': 16, '歌舞': 17
                }
                df_processed['type'] = df_processed['type'].map(type_map).fillna(0)

            # 提取需要的特征
            available_features = [f for f in self.feature_names if f in df_processed.columns]

            if len(available_features) < len(self.feature_names):
                missing = set(self.feature_names) - set(available_features)
                print(f"警告: 缺少特征 {missing}，使用默认值0")

                # 添加缺失的特征
                for f in missing:
                    df_processed[f] = 0

            # 确保特征顺序一致
            X = df_processed[self.feature_names].values

            # 处理NaN值
            X = np.nan_to_num(X, nan=0.0)

            return X

    def predict(
        self,
        movie: Movie,
        return_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        预测单个电影的票房

        Args:
            movie: Movie对象
            return_confidence: 是否返回置信区间

        Returns:
            预测结果字典
        """
        if self.model is None:
            raise RuntimeError("模型未加载")

        # 提取特征
        movie_data = self._extract_features(movie)

        # 准备特征
        X = self._prepare_features(movie_data)

        # 预测
        prediction = self.model.predict(X)[0]

        # 计算置信区间（基于训练误差的简单估计）
        confidence_lower = None
        confidence_upper = None

        if return_confidence:
            # 使用预测值的 ±20% 作为置信区间
            margin = prediction * 0.2
            confidence_lower = max(0, prediction - margin)
            confidence_upper = prediction + margin

        # 特征重要性
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
            # 归一化
            total = sum(importance.values())
            if total > 0:
                feature_importance = {k: v/total for k, v in importance.items()}
        elif hasattr(self.model, 'coef_'):
            importance = dict(zip(self.feature_names, np.abs(self.model.coef_)))
            total = sum(importance.values())
            if total > 0:
                feature_importance = {k: v/total for k, v in importance.items()}

        # 按重要性排序并转换为Python原生类型
        feature_importance = dict(
            sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        )
        # 转换numpy类型为Python原生类型
        feature_importance = {k: float(v) for k, v in feature_importance.items()}

        return {
            'predicted_box_office_wan': round(float(prediction), 2),
            'predicted_box_office': int(prediction * 10000),
            'confidence_lower_wan': round(float(confidence_lower), 2) if confidence_lower else None,
            'confidence_upper_wan': round(float(confidence_upper), 2) if confidence_upper else None,
            'confidence_lower': int(confidence_lower * 10000) if confidence_lower else None,
            'confidence_upper': int(confidence_upper * 10000) if confidence_upper else None,
            'feature_importance': feature_importance,
            'model_type': self.model_type
        }

    def predict_batch(
        self,
        movies: List[Movie],
        return_confidence: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量预测电影票房

        Args:
            movies: Movie对象列表
            return_confidence: 是否返回置信区间

        Returns:
            预测结果列表
        """
        results = []

        for movie in movies:
            try:
                result = self.predict(movie, return_confidence)
                result['movie_id'] = movie.id
                result['title'] = movie.title
                results.append(result)
            except Exception as e:
                print(f"预测失败: {movie.title}, 错误: {e}")
                results.append({
                    'movie_id': movie.id,
                    'title': movie.title,
                    'error': str(e)
                })

        return results

    def compare_models(
        self,
        movie: Movie
    ) -> Dict[str, Dict[str, Any]]:
        """
        使用所有可用模型对比预测结果

        Args:
            movie: Movie对象

        Returns:
            各模型预测结果
        """
        results = {}
        original_model_type = self.model_type

        # 尝试使用不同的模型
        for model_type in ['lr', 'xgboost']:
            try:
                # 切换模型
                self.model_type = model_type
                self._load_model()

                # 预测
                result = self.predict(movie, return_confidence=True)
                results[model_type] = result

            except Exception as e:
                print(f"模型 {model_type} 预测失败: {e}")
                results[model_type] = {'error': str(e)}

        # 恢复原模型
        self.model_type = original_model_type
        if self.model:
            self._load_model()

        return results


class PredictionSaver:
    """预测结果保存器"""

    def __init__(self):
        self.db = SessionLocal()

    def save_prediction(
        self,
        movie_id: Optional[int],
        prediction_result: Dict[str, Any],
        model_type: str = 'xgboost'
    ) -> Prediction:
        """
        保存预测结果到数据库

        Args:
            movie_id: 电影ID
            prediction_result: 预测结果
            model_type: 模型类型

        Returns:
            Prediction对象
        """
        try:
            model_type_enum = ModelType(model_type)

            prediction = Prediction(
                movie_id=movie_id,
                model_type=model_type_enum,
                predicted_box_office=prediction_result.get('predicted_box_office'),
                predicted_box_office_wan=prediction_result.get('predicted_box_office_wan'),
                confidence_lower=prediction_result.get('confidence_lower'),
                confidence_upper=prediction_result.get('confidence_upper'),
                feature_importance_dict=prediction_result.get('feature_importance', {})
            )

            self.db.add(prediction)
            self.db.commit()
            self.db.refresh(prediction)

            return prediction

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"保存预测结果失败: {e}")

    def save_batch_predictions(
        self,
        predictions: List[Dict[str, Any]],
        model_type: str = 'xgboost'
    ) -> List[Prediction]:
        """
        批量保存预测结果

        Args:
            predictions: 预测结果列表
            model_type: 模型类型

        Returns:
            Prediction对象列表
        """
        saved_predictions = []

        try:
            for pred in predictions:
                if 'error' not in pred:
                    prediction = Prediction(
                        movie_id=pred.get('movie_id'),
                        model_type=ModelType(model_type),
                        predicted_box_office=pred.get('predicted_box_office'),
                        predicted_box_office_wan=pred.get('predicted_box_office_wan'),
                        confidence_lower=pred.get('confidence_lower'),
                        confidence_upper=pred.get('confidence_upper'),
                        feature_importance_dict=pred.get('feature_importance', {})
                    )
                    self.db.add(prediction)

            self.db.commit()

            # 刷新所有对象
            for pred in self.db.new:
                self.db.refresh(pred)
                saved_predictions.append(pred)

            return saved_predictions

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"批量保存预测结果失败: {e}")

    def __del__(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()


# 全局预测器实例
_predictors = {}


def get_predictor(model_type: str = 'xgboost') -> Predictor:
    """
    获取预测器实例（单例模式）

    Args:
        model_type: 模型类型

    Returns:
        Predictor实例
    """
    if model_type not in _predictors:
        _predictors[model_type] = Predictor(model_type)
    return _predictors[model_type]


def quick_predict(movie_id: int, model_type: str = 'xgboost') -> Dict[str, Any]:
    """
    快速预测（便捷函数）

    Args:
        movie_id: 电影ID
        model_type: 模型类型

    Returns:
        预测结果
    """
    db = SessionLocal()
    try:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise ValueError(f"电影ID {movie_id} 不存在")

        predictor = get_predictor(model_type)
        result = predictor.predict(movie)

        # 保存预测结果
        saver = PredictionSaver()
        saver.save_prediction(movie_id, result, model_type)

        result['movie_id'] = movie_id
        result['title'] = movie.title

        return result

    finally:
        db.close()


if __name__ == "__main__":
    # 测试预测
    print("测试预测功能...")

    try:
        # 需要先有训练好的模型
        predictor = Predictor('xgboost')
        print("预测器初始化成功")

    except FileNotFoundError as e:
        print(f"请先训练模型: {e}")
    except Exception as e:
        print(f"预测器测试失败: {e}")
