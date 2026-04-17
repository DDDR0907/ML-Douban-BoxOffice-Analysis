"""
Movie Model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import json
import enum
from ..database import Base


class DataSource(str, enum.Enum):
    """Data source enum"""
    CRAWL = "crawl"
    UPLOAD = "upload"
    MANUAL = "manual"


class Movie(Base):
    """
    Movie information table
    """
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    douban_id = Column(String(50), unique=True, nullable=True, comment="豆瓣ID")
    movie_id = Column(String(50), nullable=True, comment="电影ID（用户上传数据）")
    title = Column(String(200), nullable=False, comment="电影名称", index=True)
    type = Column(String(100), nullable=True, comment="电影类型")
    release_date = Column(Date, nullable=True, comment="上映日期")
    release_year = Column(Integer, nullable=True, comment="上映年份", index=True)

    # 豆瓣相关字段
    rating = Column(Float, nullable=True, comment="豆瓣评分")
    rating_count = Column(Integer, nullable=True, comment="评分人数")
    wish_count = Column(Integer, nullable=True, comment="想看人数")
    tags = Column(Text, nullable=True, comment="题材标签(JSON)")
    topic_heat = Column(Integer, nullable=True, comment="话题讨论热度")

    # 票房相关字段
    box_office = Column(Integer, nullable=True, comment="实际票房（元）")
    box_office_wan = Column(Float, nullable=True, comment="票房（万元）")
    avg_price = Column(Float, nullable=True, comment="平均票价")
    per_session_attendance = Column(Integer, nullable=True, comment="场均人次")

    # 排名相关
    ranking = Column(Integer, nullable=True, comment="排名")
    list_year = Column(Integer, nullable=True, comment="上榜年份")

    # 分析字段
    positive_ratio = Column(Float, nullable=True, comment="正面评价比例")

    # 元数据
    data_source = Column(SQLEnum(DataSource), default=DataSource.UPLOAD, comment="数据来源")
    original_language = Column(String(50), nullable=True, comment="原始语言")
    production_countries = Column(String(200), nullable=True, comment="制片国家")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # Relationships
    predictions = relationship("Prediction", back_populates="movie", cascade="all, delete-orphan")

    @property
    def tags_list(self):
        """Get tags as list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []

    @tags_list.setter
    def tags_list(self, value):
        """Set tags from list"""
        if value:
            self.tags = json.dumps(value, ensure_ascii=False)
        else:
            self.tags = None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "douban_id": self.douban_id,
            "movie_id": self.movie_id,
            "title": self.title,
            "type": self.type,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "release_year": self.release_year,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "wish_count": self.wish_count,
            "tags": self.tags_list,
            "topic_heat": self.topic_heat,
            "box_office": self.box_office,
            "box_office_wan": self.box_office_wan,
            "avg_price": self.avg_price,
            "per_session_attendance": self.per_session_attendance,
            "ranking": self.ranking,
            "list_year": self.list_year,
            "positive_ratio": self.positive_ratio,
            "data_source": self.data_source.value if self.data_source else None,
            "original_language": self.original_language,
            "production_countries": self.production_countries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
