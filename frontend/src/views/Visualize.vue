<template>
  <div class="visualize">
    <el-card class="chart-selector">
      <el-radio-group v-model="currentChart" size="large">
        <el-radio-button value="rating-boxoffice">
          <el-icon><ScatterPlot /></el-icon>
          评分-票房
        </el-radio-button>
        <el-radio-button value="genre">
          <el-icon><PieChart /></el-icon>
          类型分布
        </el-radio-button>
        <el-radio-button value="model">
          <el-icon><DataAnalysis /></el-icon>
          模型对比
        </el-radio-button>
        <el-radio-button value="correlation-heatmap">
          <el-icon><Grid /></el-icon>
          相关性热力图
        </el-radio-button>
        <el-radio-button value="xgboost-feature">
          <el-icon><Histogram /></el-icon>
          XGBoost特征重要性
        </el-radio-button>
        <el-radio-button value="multi-model-feature">
          <el-icon><DataLine /></el-icon>
          多模型特征对比
        </el-radio-button>
        <el-radio-button value="year">
          <el-icon><TrendCharts /></el-icon>
          年度趋势
        </el-radio-button>
        <el-radio-button value="predict">
          <el-icon><LineChart /></el-icon>
          预测对比
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card class="chart-display">
      <div v-show="currentChart === 'rating-boxoffice'" class="chart-wrapper">
        <div class="chart-header">
          <h3>豆瓣评分 vs 票房散点图</h3>
          <p>分析电影评分与票房之间的关系</p>
        </div>
        <div ref="ratingBoxOfficeChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'genre'" class="chart-wrapper">
        <div class="chart-header">
          <h3>不同类型电影票房分布</h3>
          <p>箱线图展示各类型票房的中位数、四分位数和极值</p>
        </div>
        <div ref="genreChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'model'" class="chart-wrapper">
        <div class="chart-header">
          <h3>模型性能对比</h3>
          <p>比较不同模型在 R2、RMSE、MAE 指标上的表现</p>
        </div>
        <div ref="modelCompareChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'correlation-heatmap'" class="chart-wrapper">
        <div class="chart-header">
          <h3>数值特征与票房的相关性热力图</h3>
          <p>展示高相关数值特征与票房之间的线性相关强度</p>
        </div>
        <div ref="correlationHeatmapChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'xgboost-feature'" class="chart-wrapper">
        <div class="chart-header">
          <h3>XGBoost 特征重要性</h3>
          <p>展示 XGBoost 模型对票房预测贡献最大的特征</p>
        </div>
        <div ref="xgboostFeatureChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'multi-model-feature'" class="chart-wrapper">
        <div class="chart-header">
          <h3>多模型特征重要性对比</h3>
          <p>对比 XGBoost 与线性回归对关键特征的关注差异</p>
        </div>
        <div ref="multiModelFeatureChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'year'" class="chart-wrapper">
        <div class="chart-header">
          <h3>年度票房趋势</h3>
          <p>展示历年票房总量、电影数量和平均评分变化</p>
        </div>
        <div ref="yearTrendChart" class="chart-container"></div>
      </div>

      <div v-show="currentChart === 'predict'" class="chart-wrapper">
        <div class="chart-header">
          <h3>预测值 vs 实际值对比</h3>
          <p>评估模型票房预测结果与真实结果的偏差</p>
        </div>
        <div ref="predictChart" class="chart-container"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import {
  getFeatureCorrelationHeatmap,
  getFeatureImportance,
  getGenreDistribution,
  getModelComparison,
  getMultiModelFeatureImportance,
  getPredictComparison,
  getRatingBoxOfficeData,
  getYearTrend
} from '@/api/visualize'

const currentChart = ref('rating-boxoffice')

const ratingBoxOfficeChart = ref(null)
const genreChart = ref(null)
const modelCompareChart = ref(null)
const correlationHeatmapChart = ref(null)
const xgboostFeatureChart = ref(null)
const multiModelFeatureChart = ref(null)
const yearTrendChart = ref(null)
const predictChart = ref(null)

const charts = {}
let resizeHandler = null

const chartRefs = {
  'rating-boxoffice': ratingBoxOfficeChart,
  genre: genreChart,
  model: modelCompareChart,
  'correlation-heatmap': correlationHeatmapChart,
  'xgboost-feature': xgboostFeatureChart,
  'multi-model-feature': multiModelFeatureChart,
  year: yearTrendChart,
  predict: predictChart
}

const chartLoaders = {
  'rating-boxoffice': loadRatingBoxOfficeChart,
  genre: loadGenreChart,
  model: loadModelCompareChart,
  'correlation-heatmap': loadCorrelationHeatmapChart,
  'xgboost-feature': loadXGBoostFeatureChart,
  'multi-model-feature': loadMultiModelFeatureChart,
  year: loadYearTrendChart,
  predict: loadPredictChart
}

function getOrCreateChart(key) {
  if (!charts[key] && chartRefs[key]?.value) {
    charts[key] = echarts.init(chartRefs[key].value)
  }
  return charts[key]
}

function formatFeatureName(name, labels = {}) {
  if (labels[name]) {
    return labels[name]
  }
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

async function loadChart(type) {
  const loader = chartLoaders[type]
  if (loader) {
    await loader()
  }
}

async function loadRatingBoxOfficeChart() {
  const chart = getOrCreateChart('rating-boxoffice')
  if (!chart) return

  try {
    const data = await getRatingBoxOfficeData()
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: params => {
          const item = params.data[2]
          return `<b>${item.title}</b><br/>评分: ${item.x}<br/>票房: ${item.y.toLocaleString()} 万元<br/>类型: ${item.type || '-'}<br/>年份: ${item.year || '-'}`
        }
      },
      xAxis: {
        name: '豆瓣评分',
        nameLocation: 'center',
        nameGap: 30,
        min: 0,
        max: 10
      },
      yAxis: {
        name: '票房（万元）',
        type: 'log',
        nameLocation: 'center',
        nameGap: 50
      },
      series: [{
        type: 'scatter',
        symbolSize: 8,
        data: data.data.map(item => [item.x, item.y, item]),
        itemStyle: {
          color: '#667eea',
          opacity: 0.72
        }
      }],
      dataZoom: [
        { type: 'slider', xAxisIndex: 0 },
        { type: 'slider', yAxisIndex: 0 }
      ]
    }, true)
  } catch (error) {
    console.error('加载评分-票房散点图失败:', error)
  }
}

async function loadGenreChart() {
  const chart = getOrCreateChart('genre')
  if (!chart) return

  try {
    const data = await getGenreDistribution()
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%'
      },
      xAxis: {
        type: 'value',
        name: '票房（万元）',
        nameLocation: 'center',
        nameGap: 30
      },
      yAxis: {
        type: 'category',
        data: data.data.map(item => item.type),
        axisLabel: {
          width: 100,
          overflow: 'truncate'
        }
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
          color: '#667eea',
          borderColor: '#764ba2'
        }
      }]
    }, true)
  } catch (error) {
    console.error('加载类型分布图失败:', error)
  }
}

async function loadModelCompareChart() {
  const chart = getOrCreateChart('model')
  if (!chart) return

  try {
    const data = await getModelComparison()
    const modelNames = Object.keys(data.models || {})
    const metrics = data.metrics || ['R2', 'RMSE', 'MAE']

    if (!modelNames.length) {
      renderEmptyState(chart, data.message || '暂无模型对比数据')
      return
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: metrics
      },
      grid: {
        left: '8%',
        right: '4%',
        bottom: '12%'
      },
      xAxis: {
        type: 'category',
        data: modelNames
      },
      yAxis: {
        type: 'value'
      },
      series: metrics.map(metric => ({
        name: metric,
        type: 'bar',
        data: modelNames.map(model => data.models[model]?.[metric] ?? 0)
      }))
    }, true)
  } catch (error) {
    console.error('加载模型对比图失败:', error)
  }
}

async function loadCorrelationHeatmapChart() {
  const chart = getOrCreateChart('correlation-heatmap')
  if (!chart) return

  try {
    const data = await getFeatureCorrelationHeatmap(12)
    const features = data.features || []
    const labels = data.feature_labels || {}

    if (!features.length || !(data.matrix || []).length) {
      renderEmptyState(chart, data.message || '暂无相关性热力图数据')
      return
    }

    const categoryNames = features.map(feature => formatFeatureName(feature, labels))
    const heatmapData = []

    data.matrix.forEach((row, rowIndex) => {
      row.forEach((value, columnIndex) => {
        heatmapData.push([columnIndex, rowIndex, value])
      })
    })

    chart.setOption({
      tooltip: {
        position: 'top',
        formatter: params => {
          const [xIndex, yIndex, value] = params.data
          return `${categoryNames[yIndex]} × ${categoryNames[xIndex]}<br/>相关系数: ${Number(value).toFixed(4)}`
        }
      },
      grid: {
        top: 80,
        left: 160,
        right: 30,
        bottom: 80
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
        bottom: 20,
        inRange: {
          color: ['#1d4e89', '#dbeafe', '#fef3c7', '#c2410c']
        }
      },
      series: [{
        name: '相关性',
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true,
          formatter: params => Number(params.data[2]).toFixed(2)
        },
        emphasis: {
          itemStyle: {
            borderColor: '#333',
            borderWidth: 1
          }
        }
      }]
    }, true)
  } catch (error) {
    console.error('加载相关性热力图失败:', error)
  }
}

async function loadXGBoostFeatureChart() {
  const chart = getOrCreateChart('xgboost-feature')
  if (!chart) return

  try {
    const data = await getFeatureImportance('xgboost')
    const chartData = (data.data || []).slice().sort((a, b) => b.importance - a.importance)

    if (!chartData.length) {
      renderEmptyState(chart, data.message || '暂无 XGBoost 特征重要性数据')
      return
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '18%',
        right: '8%',
        bottom: '10%'
      },
      xAxis: {
        type: 'value',
        name: '重要性（%）',
        nameLocation: 'center',
        nameGap: 30
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

async function loadMultiModelFeatureChart() {
  const chart = getOrCreateChart('multi-model-feature')
  if (!chart) return

  try {
    const data = await getMultiModelFeatureImportance(10)
    const features = data.features || []
    const models = data.models || []

    if (!features.length || !models.length) {
      renderEmptyState(chart, data.message || '暂无多模型特征重要性对比数据')
      return
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: models.map(model => model.model_name)
      },
      grid: {
        left: '20%',
        right: '6%',
        bottom: '10%'
      },
      xAxis: {
        type: 'value',
        name: '重要性（%）',
        nameLocation: 'center',
        nameGap: 28
      },
      yAxis: {
        type: 'category',
        data: features.map(feature => formatFeatureName(feature)),
        inverse: true
      },
      series: models.map(model => ({
        name: model.model_name,
        type: 'bar',
        data: model.values,
        barMaxWidth: 18
      }))
    }, true)
  } catch (error) {
    console.error('加载多模型特征重要性对比图失败:', error)
  }
}

async function loadYearTrendChart() {
  const chart = getOrCreateChart('year')
  if (!chart) return

  try {
    const data = await getYearTrend()

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['总票房', '电影数量', '平均评分']
      },
      xAxis: {
        type: 'category',
        data: data.data.map(item => item.year)
      },
      yAxis: [
        {
          type: 'value',
          name: '票房（万元）',
          position: 'left'
        },
        {
          type: 'value',
          name: '数量/评分',
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
        },
        {
          name: '平均评分',
          type: 'line',
          yAxisIndex: 1,
          data: data.data.map(item => item.avg_rating),
          itemStyle: { color: '#e6a23c' }
        }
      ]
    }, true)
  } catch (error) {
    console.error('加载年度趋势图失败:', error)
  }
}

async function loadPredictChart() {
  const chart = getOrCreateChart('predict')
  if (!chart) return

  try {
    const data = await getPredictComparison({ limit: 20 })

    if (!(data.data || []).length) {
      renderEmptyState(chart, '暂无预测对比数据')
      return
    }

    const titles = data.data.map(item => item.title)
    const actualData = data.data.map(item => item.actual)
    const predictedData = data.data.map(item => item.predicted)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['实际票房', '预测票房']
      },
      xAxis: {
        type: 'category',
        data: titles,
        axisLabel: {
          rotate: 45,
          interval: 0,
          formatter: value => (value.length > 8 ? `${value.substring(0, 8)}...` : value)
        }
      },
      yAxis: {
        type: 'value',
        name: '票房（万元）'
      },
      series: [
        {
          name: '实际票房',
          type: 'bar',
          data: actualData,
          itemStyle: { color: '#67c23a' }
        },
        {
          name: '预测票房',
          type: 'line',
          data: predictedData,
          itemStyle: { color: '#667eea' }
        }
      ]
    }, true)
  } catch (error) {
    console.error('加载预测对比图失败:', error)
  }
}

watch(currentChart, async newValue => {
  await nextTick()
  await loadChart(newValue)
})

onMounted(async () => {
  await nextTick()
  await loadChart(currentChart.value)

  resizeHandler = () => {
    Object.values(charts).forEach(chart => chart?.resize())
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  Object.values(charts).forEach(chart => chart?.dispose())
})
</script>

<style scoped>
.visualize {
  padding: 0;
}

.chart-selector {
  margin-bottom: 20px;
}

.chart-display {
  min-height: 620px;
}

.chart-wrapper {
  width: 100%;
}

.chart-header {
  text-align: center;
  margin-bottom: 20px;
}

.chart-header h3 {
  margin: 0 0 10px 0;
  font-size: 20px;
  color: #303133;
}

.chart-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.chart-container {
  width: 100%;
  height: 520px;
}

:deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

:deep(.el-radio-button__inner) {
  padding: 12px 18px;
}

:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-left: var(--el-border-width);
  border-radius: var(--el-border-radius-base);
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: var(--el-border-radius-base);
}
</style>
