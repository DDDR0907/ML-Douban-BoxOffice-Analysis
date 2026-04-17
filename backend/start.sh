#!/bin/bash

# 豆瓣电影票房预测系统 - 后端启动脚本

cd "$(dirname "$0")"

echo "启动后端服务..."

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "警告: 未检测到虚拟环境"
    echo "建议创建虚拟环境: python3 -m venv venv"
    echo "激活虚拟环境: source venv/bin/activate"
fi

# 安装依赖（如果需要）
if [ ! -d "venv" ]; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

# 创建必要的目录
mkdir -p temp ml_models data/raw data/processed

# 启动服务器
echo "服务器启动中..."
echo "API文档地址: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务"

python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
