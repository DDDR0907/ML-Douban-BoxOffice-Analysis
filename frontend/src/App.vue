<template>
  <div class="app-container">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header>
        <div class="header-content">
          <h1 class="title">🎬 豆瓣电影票房预测系统</h1>
          <nav class="nav-menu">
            <router-link to="/" class="nav-item">
              <el-icon><DataAnalysis /></el-icon>
              数据概览
            </router-link>
            <router-link to="/data" class="nav-item">
              <el-icon><Document /></el-icon>
              数据管理
            </router-link>
            <router-link to="/model" class="nav-item">
              <el-icon><Cpu /></el-icon>
              模型训练
            </router-link>
            <router-link to="/predict" class="nav-item">
              <el-icon><TrendCharts /></el-icon>
              票房预测
            </router-link>
            <router-link to="/visualize" class="nav-item">
              <el-icon><PieChart /></el-icon>
              数据可视化
            </router-link>
          </nav>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>

      <!-- 底部 -->
      <el-footer>
        <p>© 2026 基于机器学习的电影票房分析与预测系统</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.el-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.title {
  font-size: 24px;
  margin: 0;
  font-weight: 600;
}

.nav-menu {
  display: flex;
  gap: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.3s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.2);
}

.nav-item.router-link-active {
  background: rgba(255, 255, 255, 0.3);
  font-weight: 600;
}

.el-main {
  padding: 20px;
}

.el-footer {
  background: #fff;
  border-top: 1px solid #ebeef5;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
