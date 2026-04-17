# ML-Douban-BoxOffice-Analysis

# 豆瓣电影票房预测系统 - 启动指南

## 系统架构

```
doubanban/
├── backend/           # 后端 (FastAPI + Python)
│   ├── app/
│   │   ├── api/      # API接口
│   │   ├── models/   # 数据模型
│   │   ├── schemas/  # 数据验证
│   │   ├── services/ # 业务逻辑
│   │   └── utils/    # 工具函数
│   ├── ml_models/    # 训练好的模型
│   ├── data/         # 数据文件
│   └── doubanban.db  # SQLite数据库
└── frontend/          # 前端 (Vue 3)
    └── src/
        ├── api/      # API调用
        ├── views/    # 页面组件
        ├── router/   # 路由配置
        └── assets/   # 静态资源
```

## 快速启动

### 方式一：使用启动脚本（推荐）

**后端启动：**

```bash
cd /home/test/桌面/doubanban/backend
chmod +x start.sh
./start.sh
```

**前端启动（新终端）：**

```bash
cd /home/test/桌面/doubanban/frontend
chmod +x start.sh
./start.sh
```

### 方式二：手动启动

**1. 启动后端服务**

```bash
cd /home/test/桌面/doubanban/backend

# 安装依赖（首次运行）
pip install -r requirements.txt

# 启动服务
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**2. 启动前端服务（新终端）**

```bash
cd /home/test/桌面/doubanban/frontend

# 安装依赖（首次运行）
npm install

# 启动服务
npm run dev
```

## 访问地址

- **前端界面**: http://localhost:5173
- **API文档**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 系统功能

### 1. 数据概览

- 展示系统统计数据
- 年度票房趋势图
- Top电影榜单

### 2. 数据管理

- **爬虫采集**: 配置并启动豆瓣数据爬虫
- **文件上传**: 上传Excel文件导入票房数据
- **数据列表**: 查看、搜索、删除电影数据

### 3. 模型训练

- 选择模型类型（XGBoost/线性回归）
- 配置训练参数
- 实时查看训练进度
- 查看训练结果和模型性能

### 4. 票房预测

- **单个预测**: 选择电影或手动输入特征进行预测
- **批量预测**: 上传Excel文件批量预测
- **预测历史**: 查看历史预测记录

### 5. 数据可视化

- 评分-票房散点图
- 类型票房分布箱线图
- 模型性能对比
- 特征重要性分析
- 年度趋势图
- 预测vs实际对比

## 数据导入

### Excel文件格式

支持以下字段（可包含部分字段）：

| 字段名     | 说明     | 必填 |
| ---------- | -------- | ---- |
| 片名       | 电影名称 | 是   |
| 上映年份   | 上映年份 | 否   |
| 票房(万元) | 票房数据 | 是   |
| 平均票价   | 平均票价 | 否   |
| 场均人次   | 场均人次 | 否   |
| 排名       | 排名     | 否   |

### 下载模板

在"数据管理"页面点击"下载模板"按钮获取标准模板。

## 常见问题

### 1. 后端启动失败

```bash
# 检查Python版本（需要3.8+）
python3 --version

# 重新安装依赖
pip install -r requirements.txt

# 检查数据库权限
ls -la doubanban.db
```

### 2. 前端无法连接后端

```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查CORS配置
# 确保 backend/app/config.py 中的 CORS_ORIGINS 包含前端地址
```

### 3. 模型训练失败

```bash
# 检查数据量
sqlite3 doubanban.db "SELECT COUNT(*) FROM movies WHERE box_office_wan IS NOT NULL;"

# 确保至少有100条带票房的数据
```

### 4. 爬虫无法启动

- 豆瓣可能有反爬限制，建议：
  - 降低爬取速度
  - 使用代理IP池
  - 添加请求延迟

## 开发说明

### API接口

所有API接口已在 `backend/app/api/` 目录下实现：

- `data.py` - 数据管理接口
- `crawl.py` - 爬虫接口
- `model.py` - 模型训练接口
- `predict.py` - 预测接口
- `visualize.py` - 可视化接口

### 前端组件

- `Dashboard.vue` - 数据概览
- `DataManage.vue` - 数据管理
- `ModelTrain.vue` - 模型训练
- `Predict.vue` - 票房预测
- `Visualize.vue` - 数据可视化

### 数据库模型

- `Movie` - 电影信息表
- `Prediction` - 预测记录表
- `Task` - 异步任务表

## 技术栈

**后端:**

- FastAPI - Web框架
- SQLAlchemy - ORM
- Pandas/NumPy - 数据处理
- Scikit-learn/XGBoost - 机器学习
- Jieba - 中文分词

**前端:**

- Vue 3 - 前端框架
- Element Plus - UI组件
- ECharts - 数据可视化
- Axios - HTTP客户端
- Pinia - 状态管理

## 生产环境部署

### 使用Docker Compose

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动部署

1. **后端部署**

```bash
# 使用gunicorn部署
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

2. **前端部署**

```bash
# 构建生产版本
npm run build

# 使用nginx托管
# 配置nginx指向 frontend/dist 目录
```

3. **数据库**

- 从SQLite迁移到MySQL
- 更新 `DATABASE_URL` 配置

## 许可证

本项目仅供学习研究使用。
