"""
Data Cleaner Service
数据清理服务 - 处理复杂格式的数据转换
"""
import re
import pandas as pd
from typing import Any, Optional, Dict, List


class DataCleaner:
    """数据清理服务 - 处理复杂格式的数据转换"""

    # 字段名到清理类型的映射
    FIELD_CLEAN_TYPE_MAPPING = {
        # 年份相关
        "上映年份": "year",
        "年份": "year",
        "year": "year",

        # 票房相关
        "累计票房": "box_office",
        "总票房": "box_office",
        "首周票房": "box_office",
        "首日票房": "box_office",
        "票房预测": "box_office",
        "分账票房": "box_office",
        "票房": "box_office",

        # 百分比相关
        "五星占比": "percentage",
        "四星占比": "percentage",
        "三星占比": "percentage",
        "二星占比": "percentage",
        "一星占比": "percentage",
        "占比": "percentage",

        # 人数相关
        "观众评分人数": "people_count",
        "评分人数": "people_count",
        "想看人数": "people_count",
        "评价人数": "people_count",

        # 类型相关
        "类型": "type",
        "电影类型": "type",
        "类型/版本": "type",
    }

    @staticmethod
    def parse_box_office(value: Any) -> Optional[float]:
        """
        解析票房数据

        支持格式：
        - 4266.1万 → 4266.1
        - 1.73亿 → 17300
        - 59 → 59
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 移除可能的空格和括号
        value_str = re.sub(r'\s+', '', value_str)

        # 匹配"亿"格式 (1.73亿)
        billion_match = re.search(r'([\d.]+)亿', value_str)
        if billion_match:
            try:
                return float(billion_match.group(1)) * 10000
            except (ValueError, TypeError):
                return None

        # 匹配"万"格式 (4266.1万)
        ten_thousand_match = re.search(r'([\d.]+)万', value_str)
        if ten_thousand_match:
            try:
                return float(ten_thousand_match.group(1))
            except (ValueError, TypeError):
                return None

        # 直接数字
        number_match = re.search(r'^([\d.]+)$', value_str)
        if number_match:
            try:
                return float(number_match.group(1))
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    def parse_year(value: Any) -> Optional[int]:
        """
        解析年份

        支持格式：
        - 2012-01-11 上映 → 2012
        - 2012年 → 2012
        - 2012 → 2012
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 提取4位年份
        year_match = re.search(r'(\d{4})', value_str)
        if year_match:
            try:
                year = int(year_match.group(1))
                if 1900 <= year <= 2100:
                    return year
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    def parse_percentage(value: Any) -> Optional[float]:
        """
        解析百分比

        支持格式：
        - 62.4% → 62.4
        - 62.4 → 62.4
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 移除百分号
        value_str = value_str.replace('%', '').strip()

        # 提取数字
        number_match = re.search(r'^([\d.]+)$', value_str)
        if number_match:
            try:
                return float(number_match.group(1))
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    def parse_people_count(value: Any) -> Optional[int]:
        """
        解析人数

        支持格式：
        - 1680观众评分 → 1680
        - 13万观众评分 → 130000
        - 9236人想看 → 9236
        - 15.6万人想看 → 156000
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 移除可能的空格
        value_str = re.sub(r'\s+', '', value_str)

        # 匹配"万"格式 (13万...)
        ten_thousand_match = re.search(r'([\d.]+)万', value_str)
        if ten_thousand_match:
            try:
                return int(float(ten_thousand_match.group(1)) * 10000)
            except (ValueError, TypeError):
                return None

        # 匹配纯数字开头
        number_match = re.search(r'^([\d.]+)', value_str)
        if number_match:
            try:
                return int(float(number_match.group(1)))
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    def parse_type(value: Any, take_first: bool = True) -> Optional[str]:
        """
        解析电影类型

        如果是多个类型，返回第一个或逗号分隔
        支持格式：
        - 动画,冒险,奇幻 → 动画
        - 动画 → 动画
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        if not value_str:
            return None

        # 如果是逗号分隔的多个类型
        if ',' in value_str:
            if take_first:
                # 取第一个类型
                return value_str.split(',')[0].strip()
            else:
                # 返回完整字符串
                return value_str

        return value_str

    @staticmethod
    def parse_rating(value: Any) -> Optional[float]:
        """
        解析评分

        支持格式：
        - 8.4 → 8.4
        - 8.4/10 → 8.4
        """
        if pd.isna(value):
            return None

        value_str = str(value).strip()

        # 提取数字
        rating_match = re.search(r'^([\d.]+)', value_str)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
                if 0 <= rating <= 10:
                    return rating
                elif rating > 10:
                    return rating / 10  # 可能是百分制
            except (ValueError, TypeError):
                return None

        return None

    @classmethod
    def detect_clean_type(cls, column_name: str, sample_values: List[Any]) -> Optional[str]:
        """
        检测列的清理类型

        根据列名和数据样本自动推荐清理类型
        """
        # 首先根据列名匹配
        for field_name, clean_type in cls.FIELD_CLEAN_TYPE_MAPPING.items():
            if field_name.lower() in column_name.lower():
                return clean_type

        # 根据数据样本推断
        if not sample_values:
            return None

        # 统计非空样本
        non_null_samples = [v for v in sample_values if pd.notna(v) and v != ""]
        if len(non_null_samples) < 2:
            return None

        # 检测票房类型 (包含"万"或"亿")
        for sample in non_null_samples[:5]:
            sample_str = str(sample)
            if '万' in sample_str or '亿' in sample_str:
                return "box_office"

        # 检测百分比类型 (包含"%")
        for sample in non_null_samples[:5]:
            sample_str = str(sample)
            if '%' in sample_str:
                return "percentage"

        # 检测年份类型 (包含4位数字或"上映")
        for sample in non_null_samples[:5]:
            sample_str = str(sample)
            if re.search(r'\d{4}', sample_str) or '上映' in sample_str:
                return "year"

        # 检测人数类型 (包含"人")
        for sample in non_null_samples[:5]:
            sample_str = str(sample)
            if '人' in sample_str:
                return "people_count"

        # 检测类型 (包含逗号分隔)
        for sample in non_null_samples[:5]:
            sample_str = str(sample)
            if ',' in sample_str:
                return "type"

        return None

    @classmethod
    def clean_column(cls, values: List[Any], clean_type: str) -> List[Any]:
        """
        清理整列数据

        Args:
            values: 原始数据列表
            clean_type: 清理类型

        Returns:
            清理后的数据列表
        """
        cleaned = []
        errors = []

        for idx, value in enumerate(values):
            try:
                if clean_type == "box_office":
                    result = cls.parse_box_office(value)
                elif clean_type == "year":
                    result = cls.parse_year(value)
                elif clean_type == "percentage":
                    result = cls.parse_percentage(value)
                elif clean_type == "people_count":
                    result = cls.parse_people_count(value)
                elif clean_type == "type":
                    result = cls.parse_type(value, take_first=True)
                elif clean_type == "rating":
                    result = cls.parse_rating(value)
                else:
                    result = value

                if pd.isna(value):
                    cleaned.append(None)
                else:
                    cleaned.append(result)

            except Exception as e:
                cleaned.append(value)  # 保留原值
                errors.append(f"第{idx + 1}行: {str(e)}")

        return cleaned, errors


# 全局服务实例
data_cleaner = DataCleaner()
