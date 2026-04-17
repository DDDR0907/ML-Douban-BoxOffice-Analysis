"""
Data Import Service
处理文件上传、解析、字段映射和数据导入
"""
import os
import uuid
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re

from ..config import settings
from ..models.movie import Movie, DataSource
from ..models.task import Task, TaskType, TaskStatus
from ..schemas.data import FieldMapping
from sqlalchemy.orm import Session


class DataImportService:
    """Data import service"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 缓存上传的文件数据
        self._file_cache: Dict[str, pd.DataFrame] = {}

    def save_uploaded_file(self, filename: str, content: bytes) -> Tuple[str, pd.DataFrame]:
        """
        保存上传的文件并解析

        Args:
            filename: 文件名
            content: 文件内容

        Returns:
            (file_id, dataframe)
        """
        # 生成唯一文件ID
        file_id = f"temp_{uuid.uuid4().hex[:12]}"
        file_ext = Path(filename).suffix.lower()

        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {file_ext}")

        # 保存文件
        file_path = self.upload_dir / f"{file_id}{file_ext}"
        with open(file_path, "wb") as f:
            f.write(content)

        # 解析文件
        try:
            if file_ext == ".csv":
                df = pd.read_csv(file_path, encoding="utf-8")
            else:  # .xlsx, .xls
                df = pd.read_excel(file_path)
        except Exception as e:
            # 尝试其他编码
            if file_ext == ".csv":
                try:
                    df = pd.read_csv(file_path, encoding="gbk")
                except:
                    df = pd.read_csv(file_path, encoding="gb2312")
            else:
                raise e

        # 缓存数据
        self._file_cache[file_id] = df

        return file_id, df

    def get_file_data(self, file_id: str) -> Optional[pd.DataFrame]:
        """获取缓存的文件数据"""
        return self._file_cache.get(file_id)

    def parse_release_year(self, value: Any) -> Optional[int]:
        """
        解析上映年份

        支持格式：
        - 2015
        - 2015-07-16 上映
        - 2015年
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 提取年份
        year_match = re.search(r'(\d{4})', value_str)
        if year_match:
            year = int(year_match.group(1))
            if 1900 <= year <= 2100:
                return year

        return None

    def parse_rating(self, value: Any) -> Optional[float]:
        """
        解析评分

        支持格式：
        - 8.5
        - 8.5/10
        - 6.126/10
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 提取评分
        rating_match = re.search(r'([\d.]+)', value_str)
        if rating_match:
            rating = float(rating_match.group(1))
            if 0 <= rating <= 10:
                return rating
            elif rating > 10:
                return rating / 10  # 可能是百分制

        return None

    def clean_movie_data(self, row: Dict[str, Any], mapping: FieldMapping, df_columns: List[str]) -> Dict[str, Any]:
        """
        清洗和转换电影数据

        Args:
            row: 原始数据行
            mapping: 字段映射
            df_columns: 数据框列名

        Returns:
            清洗后的数据字典
        """
        # 创建列名到值的映射
        col_map = {col.lower(): row.get(col) for col in df_columns}

        def get_value(field_name: Optional[str]) -> Any:
            """根据映射字段名获取值"""
            if not field_name or field_name.strip() == "":
                return None
            return row.get(field_name)

        # 解析上映年份
        year_value = get_value(mapping.release_year)
        release_year = self.parse_release_year(year_value)

        # 解析评分
        rating_value = get_value(mapping.rating)
        rating = self.parse_rating(rating_value)

        # 解析票房
        box_office = None
        box_office_wan = None

        # 尝试从票房(万元)字段获取
        if mapping.box_office_wan:
            bo_wan = get_value(mapping.box_office_wan)
            if pd.notna(bo_wan):
                try:
                    box_office_wan = float(bo_wan)
                    box_office = int(box_office_wan * 10000)  # 转换为元
                except:
                    pass

        # 尝试从票房(元)字段获取
        if not box_office and mapping.box_office:
            bo = get_value(mapping.box_office)
            if pd.notna(bo):
                try:
                    box_office = int(float(bo))
                    box_office_wan = box_office / 10000
                except:
                    pass

        # 解析类型（处理多个类型）
        type_value = get_value(mapping.type)
        movie_type = None
        if type_value and pd.notna(type_value):
            type_str = str(type_value).strip()
            # 如果是逗号分隔的多个类型，取第一个
            if ',' in type_str:
                movie_type = type_str.split(',')[0].strip()
            else:
                movie_type = type_str

        # 构建清洗后的数据
        cleaned_data = {
            "title": get_value(mapping.title),
            "type": movie_type,
            "release_year": release_year,
            "rating": rating,
            "rating_count": self._safe_int(get_value(mapping.rating_count)),
            "wish_count": self._safe_int(get_value(mapping.wish_count)),
            "box_office": box_office,
            "box_office_wan": box_office_wan,
            "avg_price": self._safe_float(get_value(mapping.avg_price)),
            "per_session_attendance": self._safe_int(get_value(mapping.per_session_attendance)),
            "ranking": self._safe_int(get_value(mapping.ranking)),
            "list_year": self._safe_int(get_value(mapping.list_year)),
            "movie_id": str(get_value(mapping.movie_id)) if get_value(mapping.movie_id) else None,
        }

        return cleaned_data

    def _safe_int(self, value: Any) -> Optional[int]:
        """安全转换为整数"""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except:
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except:
            return None

    def import_data(
        self,
        file_id: str,
        mapping: FieldMapping,
        db: Session,
        skip_duplicates: bool = True,
        data_source: str = "upload"
    ) -> Dict[str, Any]:
        """
        导入数据到数据库

        Args:
            file_id: 文件ID
            mapping: 字段映射
            db: 数据库会话
            skip_duplicates: 是否跳过重复数据
            data_source: 数据来源

        Returns:
            导入结果统计
        """
        # 获取文件数据
        df = self.get_file_data(file_id)
        if df is None:
            raise ValueError(f"文件不存在或已过期: {file_id}")

        # 创建任务记录
        task = Task(
            task_type=TaskType.IMPORT,
            status=TaskStatus.RUNNING,
            config_dict={"file_id": file_id, "mapping": mapping.dict(), "total_rows": len(df)}
        )
        db.add(task)
        db.commit()

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []

        try:
            for idx, row in df.iterrows():
                try:
                    # 清洗数据
                    cleaned_data = self.clean_movie_data(row, mapping, df.columns)

                    # 验证必填字段
                    if not cleaned_data.get("title"):
                        errors.append(f"第{idx + 1}行: 缺少电影名称")
                        failed_count += 1
                        continue

                    # 检查重复
                    if skip_duplicates:
                        existing = db.query(Movie).filter(
                            Movie.title == cleaned_data["title"]
                        ).first()
                        if existing:
                            skipped_count += 1
                            continue

                    # 创建电影记录
                    movie = Movie(
                        **cleaned_data,
                        data_source=DataSource(data_source)
                    )
                    db.add(movie)
                    imported_count += 1

                    # 更新进度
                    if (idx + 1) % 100 == 0:
                        task.progress = int((idx + 1) / len(df) * 100)
                        task.current_step = f"已处理 {idx + 1}/{len(df)} 条数据"
                        db.commit()

                except Exception as e:
                    failed_count += 1
                    errors.append(f"第{idx + 1}行: {str(e)}")

            # 提交所有更改
            db.commit()

            # 更新任务状态
            task.status = TaskStatus.SUCCESS
            task.progress = 100
            task.result_dict = {
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
                "errors": errors[:20]  # 只保存前20个错误
            }

        except Exception as e:
            db.rollback()
            task.status = TaskStatus.FAILED
            task.error_msg = str(e)

        finally:
            db.commit()
            # 清理缓存
            if file_id in self._file_cache:
                del self._file_cache[file_id]

        return {
            "success": task.status == TaskStatus.SUCCESS,
            "total_rows": len(df),
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "errors": errors,
            "task_id": task.id
        }

    def get_template_mapping(self, filename: str) -> Dict[str, str]:
        """
        根据文件名返回推荐的字段映射

        Args:
            filename: 文件名

        Returns:
            字段映射字典
        """
        # 电影票房.xlsx 的字段映射
        if "票房" in filename and ".xlsx" in filename:
            return {
                "title": "片名",
                "release_year": "上映年份",
                "box_office_wan": "票房(万元)",
                "avg_price": "平均票价",
                "per_session_attendance": "场均人次",
                "ranking": "排名",
                "list_year": "上榜年份",
                "movie_id": "电影id"
            }

        # enhanced_box_office_data.csv 的字段映射
        if "enhanced" in filename.lower():
            return {
                "title": "Release Group",
                "release_year": "Year",
                "box_office": "$Worldwide",
                "type": "Genres",
                "rating": "Rating",
                "rating_count": "Vote_Count",
                "original_language": "Original_Language",
                "production_countries": "Production_Countries"
            }

        return {}


# 全局服务实例
data_import_service = DataImportService()
