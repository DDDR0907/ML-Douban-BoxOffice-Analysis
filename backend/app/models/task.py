"""
Task Model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
from datetime import datetime
import json
import enum
from ..database import Base


class TaskType(str, enum.Enum):
    """Task type enum"""
    CRAWL = "crawl"
    PREPROCESS = "preprocess"
    TRAIN = "train"
    PREDICT = "predict"
    IMPORT = "import"


class TaskStatus(str, enum.Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Task(Base):
    """
    Async task record table
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    task_type = Column(SQLEnum(TaskType), nullable=False, comment="任务类型")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态")

    progress = Column(Integer, default=0, comment="进度百分比(0-100)")
    current_step = Column(String(200), nullable=True, comment="当前步骤描述")

    result = Column(Text, nullable=True, comment="任务结果(JSON)")
    error_msg = Column(Text, nullable=True, comment="错误信息")

    # 任务配置
    config = Column(Text, nullable=True, comment="任务配置(JSON)")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    @property
    def result_dict(self):
        """Get result as dict"""
        if self.result:
            try:
                return json.loads(self.result)
            except:
                return {}
        return {}

    @result_dict.setter
    def result_dict(self, value):
        """Set result from dict"""
        if value:
            self.result = json.dumps(value, ensure_ascii=False)
        else:
            self.result = None

    @property
    def config_dict(self):
        """Get config as dict"""
        if self.config:
            try:
                return json.loads(self.config)
            except:
                return {}
        return {}

    @config_dict.setter
    def config_dict(self, value):
        """Set config from dict"""
        if value:
            self.config = json.dumps(value, ensure_ascii=False)
        else:
            self.config = None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "task_type": self.task_type.value if self.task_type else None,
            "status": self.status.value if self.status else None,
            "progress": self.progress,
            "current_step": self.current_step,
            "result": self.result_dict,
            "error_msg": self.error_msg,
            "config": self.config_dict,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
