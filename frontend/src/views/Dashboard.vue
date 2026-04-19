<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
          <div class="stat-label">电影总数</div>
          <div class="stat-value">{{ overview.movies?.total || 0 }}</div>
          <div class="stat-desc">已收录电影</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #f97316 0%, #ef4444 100%)">
          <div class="stat-label">票房数据</div>
          <div class="stat-value">{{ overview.movies?.with_box_office || 0 }}</div>
          <div class="stat-desc">完整率 {{ overview.movies?.completion_rate || 0 }}%</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #0ea5e9 0%, #22d3ee 100%)">
          <div class="stat-label">预测次数</div>
          <div class="stat-value">{{ overview.predictions?.total || 0 }}</div>
          <div class="stat-desc">累计预测记录</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #22c55e 0%, #2dd4bf 100%)">
          <div class="stat-label">平均评分</div>
          <div class="stat-value">{{ overview.rating?.avg?.toFixed(1) || '-' }}</div>
          <div class="stat-desc">豆瓣评分均值</div>
        </div>
      </el-col>
    </el-row>

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

    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :lg="14">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">数值特征与票房相关性热力图</h3>
          </div>
          <div ref="correlationHeatmapChart" class="chart-container chart-tall"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="10">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">XGBoost 特征重要性</h3>
          </div>
          <div ref="xgboostFeatureChart" class="chart-container chart-tall"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="table-row">
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">票房 Top 10</h3>
            <el-button size="small" @click="loadTopMovies('box_office')">
              <el-icon><Refresh /></el-icon>
              刷新
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
            <h3 class="card-title">评分 Top 10</h3>
            <el-button size="small" @click="loadTopMovies('rating')">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
          <el-table :data="topRatingMovies" style="width: 100%" max-height="400">
            <el-table-column prop="rank" label="排名" width="60" />
            <el-table-column prop="title" label="电影名称" />
            <el-table-column prop="rating" label="评分" width="80" />
            <el-table-column prop="type" label="类型" width="120" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">数据来源分布</h3>
          </div>
          <div ref="sourceChart" class="chart-container source-chart"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  getDataOverview,
  getFeatureCorrelationHeatmap,
  getFeatureImportance,
  getGenreDistribution,
  getTopMovies,
  getYearTrend
} from '@/api/visualize'

const overview = ref({})
const topBoxOfficeMovies = ref([])
const topRatingMovies = ref([])

const yearTrendChart = ref(null)
const genreChart = ref(null)
const correlationHeatmapChart = ref(null)
const xgboostFeatureChart = ref(null)
const sourceChart = ref(null)

let yearChartInstance = null
let genreChartInstance = null
let correlationHeatmapInstance = null
let xgboostFeatureInstance = null
let sourceChartInstance = null
let resizeHandler = null

function formatNumber(num) {
  if (!num) return '-'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function formatFeatureName(name, labels = {}) {
  if (labels[name]) return labels[name]
  return String(name)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
}

function renderEmptyState(chart, message) {
  chart.setOption({
    title: {
      text: message,
      left: 'center',
      top: 'middle',
      textStyle: {
        color: '#909399',
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    xAxis: { show: false },
    yAxis: { show: false },
    visualMap: { show: false },
    series: []
  }, true)
}

async function loadOverview() {
  try {
    overview.value = await getDataOverview()
  } catch (error) {
    console.error('加载数据概览失败:', error)
  }
}

async function loadYearTrendChart() {
  try {
    const data = await getYearTrend()
    if (!yearChartInstance) {
      yearChartInstance = echarts.init(yearTrendChart.value)
    }

    yearChartInstance.setOption({
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
    }, true)
  } catch (error) {
    console.error('加载年度趋势图失败:', error)
  }
}

async function loadGenreChart() {
  try {
    const data = await getGenreDistribution()
    if (!genreChartInstance) {
      genreChartInstance = echarts.init(genreChart.value)
    }

    genreChartInstance.setOption({
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
    }, true)
  } catch (error) {
    console.error('加载类型分布图失败:', error)
  }
}

async function loadCorrelationHeatmapChart() {
  try {
    const data = await getFeatureCorrelationHeatmap(10)
    if (!correlationHeatmapInstance) {
      correlationHeatmapInstance = echarts.init(correlationHeatmapChart.value)
    }

    const features = data.features || []
    if (!features.length || !(data.matrix || []).length) {
      renderEmptyState(correlationHeatmapInstance, data.message || '暂无相关性热力图数据')
      return
    }

    const labels = data.feature_labels || {}
    const categoryNames = features.map(feature => formatFeatureName(feature, labels))
    const heatmapData = []
    data.matrix.forEach((row, rowIndex) => {
      row.forEach((value, columnIndex) => {
        heatmapData.push([columnIndex, rowIndex, value])
      })
    })

    correlationHeatmapInstance.setOption({
      tooltip: {
        position: 'top',
        formatter: params => {
          const [xIndex, yIndex, value] = params.data
          return `${categoryNames[yIndex]} × ${categoryNames[xIndex]}<br/>相关系数: ${Number(value).toFixed(4)}`
        }
      },
      grid: {
        top: 60,
        left: 150,
        right: 20,
        bottom: 70
      },
      xAxis: {
        type: 'category',
        data: categoryNames,
        splitArea: { show: true },
        axisLabel: {
          rotate: 35,
          interval: 0
        }
      },
      yAxis: {
        type: 'category',
        data: categoryNames,
        splitArea: { show: true }
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 15,
        inRange: {
          color: ['#1d4e89', '#dbeafe', '#fef3c7', '#c2410c']
        }
      },
      series: [{
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true,
          formatter: params => Number(params.data[2]).toFixed(2)
        }
      }]
    }, true)
  } catch (error) {
    console.error('加载相关性热力图失败:', error)
  }
}

async function loadXGBoostFeatureChart() {
  try {
    const data = await getFeatureImportance('xgboost')
    if (!xgboostFeatureInstance) {
      xgboostFeatureInstance = echarts.init(xgboostFeatureChart.value)
    }

    const chartData = (data.data || []).slice().sort((a, b) => b.importance - a.importance)
    if (!chartData.length) {
      renderEmptyState(xgboostFeatureInstance, data.message || '暂无 XGBoost 特征重要性数据')
      return
    }

    xgboostFeatureInstance.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '22%',
        right: '10%',
        bottom: '10%'
      },
      xAxis: {
        type: 'value',
        name: '重要性（%）',
        nameLocation: 'center',
        nameGap: 24
      },
      yAxis: {
        type: 'category',
        data: chartData.map(item => formatFeatureName(item.feature)),
        inverse: true
      },
      series: [{
        type: 'bar',
        data: chartData.map(item => item.importance),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#0f766e' },
            { offset: 1, color: '#2dd4bf' }
          ])
        },
        label: {
          show: true,
          position: 'right',
          formatter: '{c}%'
        }
      }]
    }, true)
  } catch (error) {
    console.error('加载 XGBoost 特征重要性图失败:', error)
  }
}

function loadSourceChart() {
  if (!sourceChartInstance) {
    sourceChartInstance = echarts.init(sourceChart.value)
  }

  const sources = overview.value.data_sources || []
  sourceChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{a}<br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10
    },
    series: [{
      name: '数据来源',
      type: 'pie',
      radius: ['42%', '70%'],
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
  }, true)
}

async function loadTopMovies(by) {
  try {
    const data = await getTopMovies(by, 10)
    if (by === 'box_office') {
      topBoxOfficeMovies.value = data.data
    } else {
      topRatingMovies.value = data.data
    }
  } catch (error) {
    console.error('加载 Top 电影失败:', error)
  }
}

onMounted(async () => {
  await loadOverview()
  await Promise.all([
    loadYearTrendChart(),
    loadGenreChart(),
    loadCorrelationHeatmapChart(),
    loadXGBoostFeatureChart(),
    loadTopMovies('box_office'),
    loadTopMovies('rating')
  ])
  loadSourceChart()

  resizeHandler = () => {
    yearChartInstance?.resize()
    genreChartInstance?.resize()
    correlationHeatmapInstance?.resize()
    xgboostFeatureInstance?.resize()
    sourceChartInstance?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  yearChartInstance?.dispose()
  genreChartInstance?.dispose()
  correlationHeatmapInstance?.dispose()
  xgboostFeatureInstance?.dispose()
  sourceChartInstance?.dispose()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row,
.charts-row,
.table-row {
  margin-bottom: 20px;
}

.stat-card {
  padding: 22px;
  border-radius: 16px;
  color: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
}

.stat-label {
  font-size: 14px;
  opacity: 0.92;
}

.stat-value {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
}

.stat-desc {
  margin-top: 10px;
  font-size: 13px;
  opacity: 0.9;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.chart-tall {
  height: 460px;
}

.source-chart {
  height: 320px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background: #f8fafc;
}
</style>
