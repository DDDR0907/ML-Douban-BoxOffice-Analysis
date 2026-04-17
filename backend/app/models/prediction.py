"""
Prediction Model
"""
from sqlalchemy import Column, Integer, String, BigInteger, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import json
import enum
from ..database import Base


class ModelType(str, enum.Enum):
    """Model type enum"""
    LR = "lr"  # Linear Regression
    XGBOOST = "xgboost"
    TRANSFORMER = "transformer"


class Prediction(Base):
    """
    Prediction record table
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True, comment="关联电影ID")
    model_type = Column(SQLEnum(ModelType), nullable=False, comment="模型类型")

    # 预测结果
    predicted_box_office = Column(BigInteger, nullable=True, comment="预测票房（元）")
    predicted_box_office_wan = Column(Integer, nullable=True, comment="预测票房（万元）")
    confidence_lower = Column(BigInteger, nullable=True, comment="置信区间下限")
    confidence_upper = Column(BigInteger, nullable=True, comment="置信区间上限")

    # 特征重要性
    feature_importance = Column(Text, nullable=True, comment="特征重要性(JSON)")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # Relationships
    movie = relationship("Movie", back_populates="predictions")

    @property
    def feature_importance_dict(self):
        """Get feature importance as dict"""
        if self.feature_importance:
            try:
                return json.loads(self.feature_importance)
            except:
                return {}
        return {}

    @feature_importance_dict.setter
    def feature_importance_dict(self, value):
        """Set feature importance from dict"""
        if value:
            self.feature_importance = json.dumps(value, ensure_ascii=False)
        else:
            self.feature_importance = None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "movie_id": self.movie_id,
            "model_type": self.model_type.value if self.model_type else None,
            "predicted_box_office": self.predicted_box_office,
            "predicted_box_office_wan": self.predicted_box_office_wan,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "feature_importance": self.feature_importance_dict,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
