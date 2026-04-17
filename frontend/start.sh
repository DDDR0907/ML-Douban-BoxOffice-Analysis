#!/bin/bash

# 豆瓣电影票房预测系统 - 前端启动脚本

cd "$(dirname "$0")"

echo "启动前端服务..."

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未安装Node.js"
    echo "请访问 https://nodejs.org/ 下载安装"
    exit 1
fi

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install
fi

# 启动开发服务器
echo "前端服务启动中..."
echo "访问地址: http://localhost:5173"
echo "按 Ctrl+C 停止服务"

npm run dev
