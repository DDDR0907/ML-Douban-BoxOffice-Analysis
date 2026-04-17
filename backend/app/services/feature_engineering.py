"""
Feature Engineering Module
特征工程模块 - 特征筛选、构建和标准化
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
from sklearn.feature_selection import VarianceThreshold
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
import joblib

warnings.filterwarnings('ignore')


class FeatureEngineering:
    """
    特征工程类
    """

    def __init__(self):
        self.scaler = None
        self.label_encoders = {}
        self.selected_features = None
        self.feature_importance = {}

    def analyze_correlation(
        self,
        df: pd.DataFrame,
        target_col: str = 'box_office_wan',
        method: str = 'pearson'
    ) -> pd.DataFrame:
        """
        分析特征与目标变量的相关性

        Args:
            df: 数据框
            target_col: 目标列名
            method: 相关性计算方法 (pearson, spearman, kendall)

        Returns:
            相关性矩阵
        """
        # 只选择数值型列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if target_col not in numeric_cols:
            print(f"警告: 目标列 {target_col} 不是数值型")
            return pd.DataFrame()

        # 计算相关性
        corr_matrix = df[numeric_cols].corr(method=method)

        # 提取与目标变量的相关性
        target_corr = corr_matrix[target_col].abs().sort_values(ascending=False)

        print(f"\n=== 特征与{target_col}的相关性 ({method}方法) ===")
        print(target_corr)

        return corr_matrix

    def check_vif(self, df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
        """
        计算方差膨胀因子(VIF)检查多重共线性

        Args:
            df: 数据框
            features: 特征列名列表

        Returns:
            VIF数据框
        """
        # 删除缺失值
        df_clean = df[features].dropna()

        if len(df_clean) < len(features):
            print(f"警告: 删除缺失值后样本数不足")

        # 计算VIF
        vif_data = []
        for i, feature in enumerate(features):
            try:
                vif = variance_inflation_factor(df_clean.values, i)
                vif_data.append({
                    'Feature': feature,
                    'VIF': vif,
                    'Multicollinearity': 'High' if vif > 10 else ('Moderate' if vif > 5 else 'Low')
                })
            except:
                vif_data.append({
                    'Feature': feature,
                    'VIF': np.inf,
                    'Multicollinearity': 'High'
                })

        vif_df = pd.DataFrame(vif_data).sort_values('VIF', ascending=False)

        print("\n=== 方差膨胀因子(VIF)分析 ===")
        print(vif_df)
        print("\n解释: VIF>10表示存在严重多重共线性")

        return vif_df

    def select_features_by_correlation(
        self,
        df: pd.DataFrame,
        target_col: str = 'box_office_wan',
        threshold: float = 0.1,
        max_features: int = 10
    ) -> List[str]:
        """
        基于相关性选择特征

        Args:
            df: 数据框
            target_col: 目标列
            threshold: 相关性阈值
            max_features: 最大特征数

        Returns:
            选择的特征列表
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        # 排除目标变量及其变体
        exclude_cols = [target_col, 'box_office', 'log_box_office', 'id']
        numeric_cols = [c for c in numeric_cols if c not in exclude_cols]

        # 计算相关性
        correlations = {}
        for col in numeric_cols:
            try:
                corr = df[col].corr(df[target_col])
                if not np.isnan(corr):
                    correlations[col] = abs(corr)
            except:
                pass

        # 筛选特征
        selected = sorted(
            [(k, v) for k, v in correlations.items() if v >= threshold],
            key=lambda x: x[1],
            reverse=True
        )

        # 如果没有足够特征，降低阈值
        if len(selected) < 3:
            selected = sorted(
                [(k, v) for k, v in correlations.items()],
                key=lambda x: x[1],
                reverse=True
            )[:max_features]

        features = [f[0] for f in selected[:max_features]]

        print(f"\n=== 选择的特征 (相关性阈值={threshold}) ===")
        for feat, corr in selected[:max_features]:
            print(f"  {feat}: {corr:.4f}")

        self.selected_features = features
        return features

    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        创建衍生特征

        Args:
            df: 原始数据框

        Returns:
            添加了衍生特征的数据框
        """
        df = df.copy()

        # 1. 热度强度 = 想看人数 / 评分人数
        if 'wish_count' in df.columns and 'rating_count' in df.columns:
            df['heat_intensity'] = df['wish_count'] / (df['rating_count'] + 1)
            print("✓ 创建特征: heat_intensity (热度强度)")

        # 2. 评分档期 = (评分 - 5)² (强化中等评分的影响)
        if 'rating' in df.columns:
            df['rating_squared'] = (df['rating'] - 5) ** 2
            print("✓ 创建特征: rating_squared (评分平方)")

        # 3. 是否高分电影 (评分>=8.0)
        if 'rating' in df.columns:
            df['is_high_rating'] = (df['rating'] >= 8.0).astype(int)
            print("✓ 创建特征: is_high_rating (是否高分)")

        # 4. 是否热门档期 (春节档、国庆档、暑期档)
        if 'release_date' in df.columns:
            df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
            df['release_month'] = df['release_date'].dt.month

            # 暑期档 (7-8月)、春节档 (2月)、国庆档 (10月)
            df['is_hot_season'] = df['release_month'].isin([2, 7, 8, 10]).astype(int)
            print("✓ 创建特征: is_hot_season (是否热门档期)")

        # 5. log票房 (对数变换)
        if 'box_office_wan' in df.columns:
            df['log_box_office'] = np.log1p(df['box_office_wan'])
            print("✓ 创建特征: log_box_office (对数票房)")

        # 6. 评分热度乘积
        if 'rating' in df.columns and 'rating_count' in df.columns:
            # 确保rating_count不为None
            rating_count_safe = df['rating_count'].fillna(0)
            df['rating_popularity'] = df['rating'].fillna(0) * np.log1p(rating_count_safe)
            print("✓ 创建特征: rating_popularity (评分热度乘积)")

        # 7. 年份距离 (距离2024年的年数)
        if 'release_year' in df.columns:
            df['years_since_release'] = 2024 - df['release_year']
            print("✓ 创建特征: years_since_release (发行年数)")

        # 8. 票房预期 = 平均票价 * 评分
        if 'avg_price' in df.columns and 'rating' in df.columns:
            df['price_rating_product'] = df['avg_price'].fillna(0) * df['rating'].fillna(0)
            print("✓ 创建特征: price_rating_product (票价评分乘积)")

        return df

    def remove_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = 'iqr',
        threshold: float = 3.0
    ) -> Tuple[pd.DataFrame, int]:
        """
        删除异常值

        Args:
            df: 数据框
            columns: 要检查的列
            method: 方法 ('iqr' 或 'zscore')
            threshold: 阈值 (IQR方法默认为1.5, Z-score默认为3)

        Returns:
            清洗后的数据框, 删除的行数
        """
        df_clean = df.copy()
        removed_indices = set()

        for col in columns:
            if col not in df_clean.columns:
                continue

            if method == 'iqr':
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - threshold * IQR
                upper = Q3 + threshold * IQR

                outliers = df_clean[(df_clean[col] < lower) | (df_clean[col] > upper)].index
                removed_indices.update(outliers)

            elif method == 'zscore':
                z_scores = np.abs(stats.zscore(df_clean[col].dropna()))
                outliers = df_clean[col].dropna().index[z_scores > threshold]
                removed_indices.update(outliers)

        df_clean = df_clean.drop(removed_indices)
        removed_count = len(df) - len(df_clean)

        print(f"\n=== 异常值处理 ({method}方法) ===")
        print(f"原始数据: {len(df)} 行")
        print(f"删除数据: {removed_count} 行 ({removed_count/len(df)*100:.2f}%)")
        print(f"清洗后数据: {len(df_clean)} 行")

        return df_clean, removed_count

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        numeric_strategy: str = 'median',
        categorical_strategy: str = 'mode'
    ) -> pd.DataFrame:
        """
        处理缺失值

        Args:
            df: 数据框
            numeric_strategy: 数值型列的处理策略 ('mean', 'median', 'zero')
            categorical_strategy: 分类型列的处理策略 ('mode', 'constant')

        Returns:
            处理后的数据框
        """
        df_clean = df.copy()

        # 处理数值型列
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            if df_clean[col].isnull().sum() > 0:
                if numeric_strategy == 'mean':
                    df_clean[col].fillna(df_clean[col].mean(), inplace=True)
                elif numeric_strategy == 'median':
                    df_clean[col].fillna(df_clean[col].median(), inplace=True)
                elif numeric_strategy == 'zero':
                    df_clean[col].fillna(0, inplace=True)

                print(f"✓ {col}: 使用{numeric_strategy}填补 {df_clean[col].isnull().sum()} 个缺失值")

        # 处理分类型列
        categorical_cols = df_clean.select_dtypes(include=['object']).columns.tolist()
        for col in categorical_cols:
            if df_clean[col].isnull().sum() > 0:
                if categorical_strategy == 'mode':
                    mode_val = df_clean[col].mode()
                    if len(mode_val) > 0:
                        df_clean[col].fillna(mode_val[0], inplace=True)
                elif categorical_strategy == 'constant':
                    df_clean[col].fillna('Unknown', inplace=True)

                print(f"✓ {col}: 使用{categorical_strategy}填补 {df_clean[col].isnull().sum()} 个缺失值")

        return df_clean

    def normalize_features(
        self,
        df: pd.DataFrame,
        features: List[str],
        method: str = 'minmax'
    ) -> pd.DataFrame:
        """
        特征标准化

        Args:
            df: 数据框
            features: 要标准化的特征列表
            method: 标准化方法 ('minmax' 或 'standard')

        Returns:
            标准化后的数据框
        """
        df_normalized = df.copy()

        if method == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            self.scaler = StandardScaler()

        # 删除缺失值后进行标准化
        df_clean = df_normalized[features].dropna()

        if len(df_clean) > 0:
            normalized_values = self.scaler.fit_transform(df_clean)
            df_normalized.loc[df_clean.index, features] = normalized_values

            print(f"\n=== 特征标准化 ({method}方法) ===")
            print(f"标准化特征: {features}")

        return df_normalized

    def encode_categorical_features(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        method: str = 'label'
    ) -> pd.DataFrame:
        """
        编码分类型特征

        Args:
            df: 数据框
            categorical_cols: 分类特征列
            method: 编码方法 ('label' 或 'onehot')

        Returns:
            编码后的数据框
        """
        df_encoded = df.copy()

        for col in categorical_cols:
            if col not in df_encoded.columns:
                continue

            if method == 'label':
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df_encoded[col] = self.label_encoders[col].fit_transform(
                        df_encoded[col].astype(str)
                    )
                else:
                    df_encoded[col] = self.label_encoders[col].transform(
                        df_encoded[col].astype(str)
                    )

            elif method == 'onehot':
                dummies = pd.get_dummies(df_encoded[col], prefix=col, drop_first=True)
                df_encoded = pd.concat([df_encoded, dummies], axis=1)
                df_encoded.drop(col, axis=1, inplace=True)

            print(f"✓ {col}: 使用{method}编码")

        return df_encoded

    def prepare_features_for_model(
        self,
        df: pd.DataFrame,
        target_col: str = 'box_office_wan',
        feature_selection: bool = True,
        create_derived: bool = True,
        handle_missing: bool = True,
        normalize: bool = True
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        完整的特征工程流程

        Args:
            df: 原始数据框
            target_col: 目标列
            feature_selection: 是否进行特征选择
            create_derived: 是否创建衍生特征
            handle_missing: 是否处理缺失值
            normalize: 是否标准化

        Returns:
            处理后的数据框, 特征列表
        """
        print("="*60)
        print("开始特征工程处理")
        print("="*60)

        df_processed = df.copy()

        # 1. 处理缺失值
        if handle_missing:
            print("\n[1/6] 处理缺失值...")
            df_processed = self.handle_missing_values(df_processed)

        # 2. 创建衍生特征
        if create_derived:
            print("\n[2/6] 创建衍生特征...")
            df_processed = self.create_derived_features(df_processed)

        # 3. 编码分类特征
        print("\n[3/6] 编码分类特征...")
        categorical_cols = df_processed.select_dtypes(include=['object']).columns.tolist()
        # 排除某些不需要编码的列
        exclude_cols = ['title', 'douban_id', 'movie_id', 'release_date']
        categorical_cols = [c for c in categorical_cols if c not in exclude_cols]
        df_processed = self.encode_categorical_features(df_processed, categorical_cols)

        # 4. 特征选择
        if feature_selection:
            print("\n[4/6] 特征选择...")
            # 相关性分析
            self.analyze_correlation(df_processed, target_col)

            # 选择高相关特征
            self.selected_features = self.select_features_by_correlation(
                df_processed, target_col, threshold=0.01, max_features=15
            )

            features = self.selected_features.copy()
        else:
            # 排除目标变量及其变体
            exclude_cols = [target_col, 'box_office', 'log_box_office', 'id']
            numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
            features = [c for c in numeric_cols if c not in exclude_cols]

        # 5. 标准化
        if normalize:
            print("\n[5/6] 特征标准化...")
            df_processed = self.normalize_features(df_processed, features)

        # 6. 删除包含缺失值的行
        print("\n[6/6] 清理数据...")
        final_cols = features + [target_col]
        df_processed = df_processed[final_cols].dropna()

        print(f"\n特征工程完成!")
        print(f"最终数据: {len(df_processed)} 行 x {len(features)} 个特征")
        print(f"特征列表: {features}")

        return df_processed, features


class FeaturePipeline:
    """
    统一的特征工程管道
    确保训练和预测时使用完全一致的特征处理逻辑
    """

    def __init__(self):
        self.scaler = None
        self.label_encoders = {}
        self.fill_strategies = {}
        self.final_features = []

    def fit(self, df: pd.DataFrame, target_col: str = 'box_office_wan'):
        """
        训练模式：学习所有参数

        Args:
            df: 原始数据框
            target_col: 目标列名

        Returns:
            self
        """
        # 1. 转换时间特征
        df = self._convert_time_features(df)

        # 2. 学习缺失值填充策略
        self._learn_missing_value_strategy(df)

        # 3. 创建衍生特征
        df = self._create_derived_features(df)

        # 4. 编码分类特征
        self._fit_categorical_encoders(df)

        # 5. 特征选择
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = [target_col, 'box_office', 'log_box_office', 'id']
        self.final_features = [c for c in numeric_cols if c not in exclude_cols]

        # 6. 训练标准化器
        self.scaler = MinMaxScaler()
        df_clean = df[self.final_features].dropna()
        if len(df_clean) > 0:
            self.scaler.fit(df_clean)

        print(f"✓ FeaturePipeline 训练完成，使用 {len(self.final_features)} 个特征")
        print(f"  特征列表: {self.final_features}")

        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        预测模式：应用学习的参数

        Args:
            df: 原始数据框

        Returns:
            特征数组
        """
        df = df.copy()

        # 1. 转换时间特征
        df = self._convert_time_features(df)

        # 2. 应用缺失值填充
        df = self._apply_missing_value_strategy(df)

        # 3. 创建衍生特征
        df = self._create_derived_features(df)

        # 4. 应用编码
        df = self._apply_categorical_encoders(df)

        # 5. 确保所有特征存在
        for f in self.final_features:
            if f not in df.columns:
                df[f] = 0

        # 6. 应用标准化
        if self.scaler is not None and len(df) > 0:
            df_clean = df[self.final_features].fillna(0)
            df[self.final_features] = self.scaler.transform(df_clean)

        # 7. 返回特征数组
        X = df[self.final_features].values
        X = np.nan_to_num(X, nan=0.0)

        return X

    def fit_transform(self, df: pd.DataFrame, target_col: str = 'box_office_wan') -> np.ndarray:
        """
        训练并转换

        Args:
            df: 原始数据框
            target_col: 目标列名

        Returns:
            特征数组
        """
        self.fit(df, target_col)
        return self.transform(df)

    def _convert_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """将时间特征转换为数值"""
        df = df.copy()

        for col in ['created_at', 'updated_at']:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].apply(
                        lambda x: x.timestamp() if pd.notna(x) else None
                    )

        return df

    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建衍生特征"""
        df = df.copy()

        # 1. 热度强度 = 想看人数 / 评分人数
        if 'wish_count' in df.columns and 'rating_count' in df.columns:
            df['heat_intensity'] = df['wish_count'] / (df['rating_count'] + 1)

        # 2. 评分档期 = (评分 - 5)²
        if 'rating' in df.columns:
            df['rating_squared'] = (df['rating'] - 5) ** 2

        # 3. 是否高分电影
        if 'rating' in df.columns:
            df['is_high_rating'] = (df['rating'] >= 8.0).astype(int)

        # 4. log票房
        if 'box_office_wan' in df.columns:
            df['log_box_office'] = np.log1p(df['box_office_wan'])

        # 5. 评分热度乘积
        if 'rating' in df.columns and 'rating_count' in df.columns:
            rating_count_safe = df['rating_count'].fillna(0)
            df['rating_popularity'] = df['rating'].fillna(0) * np.log1p(rating_count_safe)

        # 6. 年份距离
        if 'release_year' in df.columns:
            df['years_since_release'] = 2024 - df['release_year']

        # 7. 票房预期
        if 'avg_price' in df.columns and 'rating' in df.columns:
            df['price_rating_product'] = df['avg_price'].fillna(0) * df['rating'].fillna(0)

        return df

    def _learn_missing_value_strategy(self, df: pd.DataFrame):
        """学习缺失值填充策略"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().sum() > 0:
                self.fill_strategies[col] = df[col].median()

        categorical_cols = df.select_dtypes(include=['object']).columns
        exclude_cols = ['title', 'douban_id', 'movie_id', 'release_date']
        for col in categorical_cols:
            if col not in exclude_cols and df[col].isnull().sum() > 0:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    self.fill_strategies[col] = mode_val[0]

    def _apply_missing_value_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用缺失值填充策略"""
        df = df.copy()

        for col, value in self.fill_strategies.items():
            if col in df.columns:
                df[col].fillna(value, inplace=True)

        return df

    def _fit_categorical_encoders(self, df: pd.DataFrame):
        """训练分类编码器"""
        categorical_cols = df.select_dtypes(include=['object']).columns
        exclude_cols = ['title', 'douban_id', 'movie_id', 'release_date']

        for col in categorical_cols:
            if col not in exclude_cols:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[col] = self.label_encoders[col].fit_transform(
                        df[col].astype(str)
                    )

    def _apply_categorical_encoders(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用分类编码器"""
        df = df.copy()

        for col, encoder in self.label_encoders.items():
            if col in df.columns:
                # 处理未见过的类别
                df[col] = df[col].astype(str)
                # 将未见过的类别映射为0
                df[col] = df[col].apply(
                    lambda x: x if x in set(encoder.classes_) else list(encoder.classes_)[0] if len(encoder.classes_) > 0 else 0
                )
                try:
                    df[col] = encoder.transform(df[col])
                except ValueError:
                    df[col] = 0

        return df

    def save(self, path: str):
        """保存管道"""
        joblib.dump({
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'fill_strategies': self.fill_strategies,
            'final_features': self.final_features
        }, path)
        print(f"✓ FeaturePipeline 已保存到: {path}")

    def load(self, path: str):
        """加载管道"""
        data = joblib.load(path)
        self.scaler = data.get('scaler')
        self.label_encoders = data.get('label_encoders', {})
        self.fill_strategies = data.get('fill_strategies', {})
        self.final_features = data.get('final_features', [])
        print(f"✓ FeaturePipeline 已从 {path} 加载")
        print(f"  特征数量: {len(self.final_features)}")


# 全局特征工程实例
feature_engineering = FeatureEngineering()
