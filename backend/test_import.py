#!/usr/bin/env python
"""
数据导入测试脚本
测试将电影票房.xlsx数据导入数据库
"""
import sys
sys.path.insert(0, '/home/test/桌面/doubanban/backend')

from app.database import SessionLocal, init_db
from app.services.data_import import data_import_service
from app.schemas.data import FieldMapping
import pandas as pd

# 初始化数据库
print("初始化数据库...")
init_db()
db = SessionLocal()

# 读取Excel文件
excel_path = "/home/test/桌面/doubanban/电影票房.xlsx"
print(f"读取文件: {excel_path}")

# 保存文件（模拟上传）
with open(excel_path, 'rb') as f:
    content = f.read()
    file_id, df = data_import_service.save_uploaded_file("电影票房.xlsx", content)

print(f"✓ 文件已加载")
print(f"  - 总行数: {len(df)}")
print(f"  - 列名: {df.columns.tolist()}")
print(f"  - 文件ID: {file_id}")

# 显示前几行数据预览
print("\n数据预览（前5行）:")
print(df.head(5).to_string())

# 使用自动推荐的字段映射
print("\n使用自动字段映射...")

mapping = FieldMapping(
    title="片名",
    release_year="上映年份",
    box_office_wan="票房(万元)",
    avg_price="平均票价",
    per_session_attendance="场均人次",
    ranking="排名",
    list_year="上榜年份",
    movie_id="电影id"
)

# 导入数据
print("\n开始导入数据...")
result = data_import_service.import_data(
    file_id=file_id,
    mapping=mapping,
    db=db,
    skip_duplicates=True,
    data_source="upload"
)

print("\n" + "="*50)
print("导入结果:")
print(f"  总行数: {result['total_rows']}")
print(f"  成功导入: {result['imported_count']}")
print(f"  跳过重复: {result['skipped_count']}")
print(f"  失败: {result['failed_count']}")

if result['errors']:
    print(f"\n错误信息（前10条）:")
    for error in result['errors'][:10]:
        print(f"  - {error}")

# 查询数据库确认
from app.models.movie import Movie
total = db.query(Movie).count()
print(f"\n数据库中当前电影总数: {total}")

# 显示几条导入的数据
movies = db.query(Movie).limit(5).all()
print("\n导入的示例数据:")
for m in movies:
    print(f"  - {m.title} ({m.release_year}) | 票房: {m.box_office_wan}万元 | 评分: {m.rating}")

db.close()
print("\n✓ 导入完成!")
