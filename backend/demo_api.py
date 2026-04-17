#!/usr/bin/env python
"""
API演示脚本 - 展示所有主要API功能
"""
import json
import requests

BASE_URL = "http://localhost:8888"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def main():
    # 1. 系统信息
    print_section("1. 系统信息")
    r = requests.get(f"{BASE_URL}/")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    # 2. 数据统计
    print_section("2. 数据统计概览")
    r = requests.get(f"{BASE_URL}/api/data/stats")
    stats = r.json()
    print(f"总电影数: {stats['total_movies']}")
    print(f"总票房: {stats['total_box_office']:.0f}万元 ({stats['total_box_office']/100000:.0f}亿元)")
    print(f"平均评分: {stats['avg_rating']}")
    print(f"年份分布: {dict(list(stats['year_distribution'].items())[:5])}...")
    print(f"类型分布: {dict(list(stats['genre_distribution'].items())[:5])}...")

    # 3. 电影列表
    print_section("3. 电影列表（分页）")
    r = requests.get(f"{BASE_URL}/api/data/movies?page=1&page_size=10")
    data = r.json()
    print(f"总记录: {data['total']} | 当前页: {data['page']}/{data['page_size']}")
    print("\n最近添加的电影:")
    for m in data['data'][:5]:
        print(f"  - {m['title']} ({m['release_year']}) | {m['box_office_wan']:.0f}万元 | {m['type'] or '未知类型'}")

    # 4. Top票房电影
    print_section("4. Top 10 票房电影")
    r = requests.get(f"{BASE_URL}/api/visualize/top-movies?by=box_office&limit=10")
    data = r.json()
    for m in data['data']:
        print(f"  {m['rank']:2d}. {m['title']:<20s} - {m['box_office']:>12.0f}万元 ({m['year']})")

    # 5. 年度票房趋势
    print_section("5. 年度票房趋势（近10年）")
    r = requests.get(f"{BASE_URL}/api/visualize/year-trend")
    data = r.json()
    print(f"{'年份':<6} {'总票房(万元)':>15} {'电影数':>8} {'平均评分':>8}")
    print("-" * 40)
    for y in data['data'][-10:]:
        rating = f"{y['avg_rating']:.2f}" if y['avg_rating'] else "N/A"
        print(f"{y['year']:<6} {y['total_box_office']:>15.0f} {y['movie_count']:>8} {rating:>8}")

    # 6. 类型票房分布
    print_section("6. 电影类型票房分布")
    r = requests.get(f"{BASE_URL}/api/visualize/genre-distribution")
    data = r.json()
    print(f"{'类型':<15} {'中位数(万)':>12} {'最大值(万)':>12} {'电影数':>8}")
    print("-" * 50)
    for g in data['data'][:10]:
        print(f"{g['type']:<15} {g['median']:>12.0f} {g['max']:>12.0f} {len(g['values']):>8}")

    # 7. 模型性能对比
    print_section("7. 模型性能对比")
    r = requests.get(f"{BASE_URL}/api/visualize/model-comparison")
    data = r.json()
    print(f"指标: {', '.join(data['metrics'])}")
    print()
    for model, metrics in data['models'].items():
        print(f"{model}:")
        for metric, value in metrics.items():
            print(f"  - {metric}: {value}")

    # 8. 特征重要性
    print_section("8. 特征重要性（XGBoost）")
    r = requests.get(f"{BASE_URL}/api/visualize/feature-importance?model_type=xgboost")
    data = r.json()
    for f in data['data']:
        print(f"  {f['feature']:<15} {f['importance']:>6.2%}")

    # 9. 爬虫配置
    print_section("9. 爬虫配置")
    r = requests.get(f"{BASE_URL}/api/crawl/config")
    print(json.dumps(r.json(), indent=2))

    # 10. 文件模板下载
    print_section("10. 数据导入模板")
    print(f"下载链接: {BASE_URL}/api/data/template")
    print("支持的文件格式: .xlsx, .xls, .csv")

    print("\n" + "="*60)
    print("  API演示完成！访问 http://localhost:8888/docs 查看完整文档")
    print("="*60)

if __name__ == "__main__":
    main()
