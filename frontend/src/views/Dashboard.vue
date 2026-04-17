<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
          <div class="stat-label">总电影数</div>
          <div class="stat-value">{{ overview.movies?.total || 0 }}</div>
          <div class="stat-desc">已收录电影</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
          <div class="stat-label">票房数据</div>
          <div class="stat-value">{{ overview.movies?.with_box_office || 0 }}</div>
          <div class="stat-desc">完整度 {{ overview.movies?.completion_rate || 0 }}%</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
          <div class="stat-label">预测次数</div>
          <div class="stat-value">{{ overview.predictions?.total || 0 }}</div>
          <div class="stat-desc">累计预测</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)">
          <div class="stat-label">平均评分</div>
          <div class="stat-value">{{ overview.rating?.avg?.toFixed(1) || '-' }}</div>
          <div class="stat-desc">豆瓣评分</div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">年度票房趋势</h3>
          </div>
          <div ref="yearTrendChart" class="chart-container"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">类型票房分布</h3>
          </div>
          <div ref="genreChart" class="chart-container"></div>
        </div>
      </el-col>
    </el-row>

    <!-- Top电影列表 -->
    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">票房Top 10</h3>
            <el-button size="small" @click="loadTopMovies('box_office')">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
          <el-table :data="topBoxOfficeMovies" style="width: 100%" max-height="400">
            <el-table-column prop="rank" label="排名" width="60" />
            <el-table-column prop="title" label="电影名称" />
            <el-table-column prop="box_office" label="票房(万元)" :formatter="row => formatNumber(row.box_office)" />
            <el-table-column prop="year" label="年份" width="80" />
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">评分Top 10</h3>
            <el-button size="small" @click="loadTopMovies('rating')">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
          <el-table :data="topRatingMovies" style="width: 100%" max-height="400">
            <el-table-column prop="rank" label="排名" width="60" />
            <el-table-column prop="title" label="电影名称" />
            <el-table-column prop="rating" label="评分" width="80" />
            <el-table-column prop="type" label="类型" width="100" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <!-- 数据来源分布 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">数据来源分布</h3>
          </div>
          <div ref="sourceChart" class="chart-container" style="height: 300px;"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getDataOverview, getYearTrend, getTopMovies, getGenreDistribution } from '@/api/visualize'

const overview = ref({})
const yearTrendChart = ref(null)
const genreChart = ref(null)
const sourceChart = ref(null)
const topBoxOfficeMovies = ref([])
const topRatingMovies = ref([])

let yearChart = null
let genreChartInstance = null
let sourceChartInstance = null

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '-'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

// 加载数据概览
const loadOverview = async () => {
  try {
    const data = await getDataOverview()
    overview.value = data
  } catch (error) {
    console.error('加载数据概览失败:', error)
  }
}

// 加载年度趋势图
const loadYearTrendChart = async () => {
  try {
    const data = await getYearTrend()

    if (!yearChart) {
      yearChart = echarts.init(yearTrendChart.value)
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['总票房', '电影数量']
      },
      xAxis: {
        type: 'category',
        data: data.data.map(item => item.year)
      },
      yAxis: [
        {
          type: 'value',
          name: '票房(万元)',
          position: 'left'
        },
        {
          type: 'value',
          name: '数量',
          position: 'right'
        }
      ],
      series: [
        {
          name: '总票房',
          type: 'line',
          data: data.data.map(item => item.total_box_office),
          smooth: true,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
            ])
          }
        },
        {
          name: '电影数量',
          type: 'bar',
          yAxisIndex: 1,
          data: data.data.map(item => item.movie_count),
          itemStyle: { color: '#67c23a' }
        }
      ]
    }

    yearChart.setOption(option)
  } catch (error) {
    console.error('加载年度趋势图失败:', error)
  }
}

// 加载类型分布图
const loadGenreChart = async () => {
  try {
    const data = await getGenreDistribution()

    if (!genreChartInstance) {
      genreChartInstance = echarts.init(genreChart.value)
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      xAxis: {
        type: 'value',
        name: '票房(万元)'
      },
      yAxis: {
        type: 'category',
        data: data.data.map(item => item.type)
      },
      series: [{
        type: 'boxplot',
        data: data.data.map(item => [
          item.min,
          item.q1,
          item.median,
          item.q3,
          item.max
        ]),
        itemStyle: {
          color: '#667eea'
        }
      }]
    }

    genreChartInstance.setOption(option)
  } catch (error) {
    console.error('加载类型分布图失败:', error)
  }
}

// 加载数据来源图
const loadSourceChart = () => {
  if (!sourceChartInstance) {
    sourceChartInstance = echarts.init(sourceChart.value)
  }

  const sources = overview.value.data_sources || []
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10
    },
    series: [{
      name: '数据来源',
      type: 'pie',
      radius: ['40%', '70%'],
      data: sources.map(item => ({
        value: item.count,
        name: item.source === 'crawl' ? '爬虫获取' : item.source === 'upload' ? '文件上传' : '手动录入'
      })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }

  sourceChartInstance.setOption(option)
}

// 加载Top电影
const loadTopMovies = async (by) => {
  try {
    const data = await getTopMovies(by, 10)
    if (by === 'box_office') {
      topBoxOfficeMovies.value = data.data
    } else {
      topRatingMovies.value = data.data
    }
  } catch (error) {
    console.error('加载Top电影失败:', error)
  }
}

// 初始化
onMounted(async () => {
  await loadOverview()
  await loadYearTrendChart()
  await loadGenreChart()
  await loadTopMovies('box_office')
  await loadTopMovies('rating')

  // 数据来源图需要等待概览数据加载完成
  setTimeout(() => {
    loadSourceChart()
  }, 500)

  // 响应式
  window.addEventListener('resize', () => {
    yearChart?.resize()
    genreChartInstance?.resize()
    sourceChartInstance?.resize()
  })
})

onUnmounted(() => {
  yearChart?.dispose()
  genreChartInstance?.dispose()
  sourceChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-container {
  width: 100%;
  height: 400px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background: #f5f7fa;
}
</style>
