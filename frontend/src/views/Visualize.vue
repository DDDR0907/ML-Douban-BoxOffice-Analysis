<template>
  <div class="visualize">
    <!-- 图表类型选择 -->
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
        <el-radio-button value="feature">
          <el-icon><Histogram /></el-icon>
          特征重要性
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

    <!-- 图表展示区 -->
    <el-card class="chart-display">
      <!-- 评分-票房散点图 -->
      <div v-show="currentChart === 'rating-boxoffice'" class="chart-wrapper">
        <div class="chart-header">
          <h3>豆瓣评分 vs 票房散点图</h3>
          <p>分析电影评分与票房之间的关系</p>
        </div>
        <div ref="ratingBoxOfficeChart" class="chart-container"></div>
      </div>

      <!-- 类型票房分布 -->
      <div v-show="currentChart === 'genre'" class="chart-wrapper">
        <div class="chart-header">
          <h3>不同类型电影票房分布</h3>
          <p>箱线图展示各类型票房的中位数、四分位数和极值</p>
        </div>
        <div ref="genreChart" class="chart-container"></div>
      </div>

      <!-- 模型性能对比 -->
      <div v-show="currentChart === 'model'" class="chart-wrapper">
        <div class="chart-header">
          <h3>模型性能对比</h3>
          <p>不同模型在R²、RMSE、MAE指标上的表现</p>
        </div>
        <div ref="modelCompareChart" class="chart-container"></div>
      </div>

      <!-- 特征重要性 -->
      <div v-show="currentChart === 'feature'" class="chart-wrapper">
        <div class="chart-header">
          <h3>特征重要性分析</h3>
          <p>
            模型训练时各特征对预测结果的贡献度
            <el-select v-model="featureModelType" size="small" style="margin-left: 10px">
              <el-option label="XGBoost" value="xgboost"></el-option>
              <el-option label="线性回归" value="lr"></el-option>
            </el-select>
          </p>
        </div>
        <div ref="featureChart" class="chart-container"></div>
      </div>

      <!-- 年度趋势 -->
      <div v-show="currentChart === 'year'" class="chart-wrapper">
        <div class="chart-header">
          <h3>年度票房趋势</h3>
          <p>展示历年票房总量和电影数量变化</p>
        </div>
        <div ref="yearTrendChart" class="chart-container"></div>
      </div>

      <!-- 预测对比 -->
      <div v-show="currentChart === 'predict'" class="chart-wrapper">
        <div class="chart-header">
          <h3>预测值 vs 实际值对比</h3>
          <p>评估模型预测准确性</p>
        </div>
        <div ref="predictChart" class="chart-container"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getRatingBoxOfficeData,
  getGenreDistribution,
  getModelComparison,
  getFeatureImportance,
  getYearTrend,
  getPredictComparison
} from '@/api/visualize'

const currentChart = ref('rating-boxoffice')
const featureModelType = ref('xgboost')

// 图表引用
const ratingBoxOfficeChart = ref(null)
const genreChart = ref(null)
const modelCompareChart = ref(null)
const featureChart = ref(null)
const yearTrendChart = ref(null)
const predictChart = ref(null)

// 图表实例
let charts = {}

// 切换图表时重新加载
watch(currentChart, async (newVal) => {
  await nextTick()
  loadChart(newVal)
})

watch(featureModelType, () => {
  if (currentChart.value === 'feature') {
    loadFeatureChart()
  }
})

// 加载指定图表
const loadChart = async (type) => {
  switch (type) {
    case 'rating-boxoffice':
      loadRatingBoxOfficeChart()
      break
    case 'genre':
      loadGenreChart()
      break
    case 'model':
      loadModelCompareChart()
      break
    case 'feature':
      loadFeatureChart()
      break
    case 'year':
      loadYearTrendChart()
      break
    case 'predict':
      loadPredictChart()
      break
  }
}

// 评分-票房散点图
const loadRatingBoxOfficeChart = async () => {
  try {
    const data = await getRatingBoxOfficeData()

    if (!charts.ratingBoxOffice) {
      charts.ratingBoxOffice = echarts.init(ratingBoxOfficeChart.value)
    }

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          return `<b>${params.data.title}</b><br/>
                  评分: ${params.data.x}<br/>
                  票房: ${params.data.y.toLocaleString()} 万元<br/>
                  类型: ${params.data.type}<br/>
                  年份: ${params.data.year}`
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
          opacity: 0.7
        }
      }],
      dataZoom: [
        { type: 'slider', xAxisIndex: 0 },
        { type: 'slider', yAxisIndex: 0 }
      ]
    }

    charts.ratingBoxOffice.setOption(option)
  } catch (error) {
    console.error('加载散点图失败:', error)
  }
}

// 类型票房分布箱线图
const loadGenreChart = async () => {
  try {
    const data = await getGenreDistribution()

    if (!charts.genre) {
      charts.genre = echarts.init(genreChart.value)
    }

    const option = {
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
          width: 80,
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
        },
        emphasis: {
          itemStyle: {
            color: '#764ba2'
          }
        }
      }]
    }

    charts.genre.setOption(option)
  } catch (error) {
    console.error('加载类型图失败:', error)
  }
}

// 模型性能对比
const loadModelCompareChart = async () => {
  try {
    const data = await getModelComparison()

    if (!charts.modelCompare) {
      charts.modelCompare = echarts.init(modelCompareChart.value)
    }

    const models = Object.keys(data.models)
    const metrics = data.metrics || ['R²', 'RMSE', 'MAE']

    const series = metrics.map(metric => ({
      name: metric,
      type: 'bar',
      data: models.map(model => data.models[model][metric] || 0)
    }))

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: metrics
      },
      xAxis: {
        type: 'category',
        data: models.map(m => m === 'xgboost' ? 'XGBoost' : m === 'lr' ? '线性回归' : m)
      },
      yAxis: {
        type: 'value'
      },
      series: series
    }

    charts.modelCompare.setOption(option)
  } catch (error) {
    console.error('加载模型对比图失败:', error)
  }
}

// 特征重要性
const loadFeatureChart = async () => {
  try {
    const data = await getFeatureImportance(featureModelType.value)

    if (!charts.feature) {
      charts.feature = echarts.init(featureChart.value)
    }

    const chartData = (data.data || []).sort((a, b) => b.importance - a.importance)

    if (chartData.length === 0) {
      charts.feature.setOption({
        title: {
          text: data.message || '暂无特征重要性数据，请先训练模型',
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
        series: []
      }, true)
      return
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '15%',
        right: '5%',
        bottom: '10%'
      },
      xAxis: {
        type: 'value',
        name: '重要性 (%)',
        nameLocation: 'center',
        nameGap: 30
      },
      yAxis: {
        type: 'category',
        data: chartData.map(item => item.feature),
        inverse: true
      },
      series: [{
        type: 'bar',
        data: chartData.map(item => item.importance),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        },
        label: {
          show: true,
          position: 'right',
          formatter: '{c}%'
        }
      }]
    }

    charts.feature.setOption(option)
  } catch (error) {
    console.error('加载特征重要性图失败:', error)
  }
}

// 年度趋势
const loadYearTrendChart = async () => {
  try {
    const data = await getYearTrend()

    if (!charts.yearTrend) {
      charts.yearTrend = echarts.init(yearTrendChart.value)
    }

    const option = {
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
    }

    charts.yearTrend.setOption(option)
  } catch (error) {
    console.error('加载年度趋势图失败:', error)
  }
}

// 预测对比图
const loadPredictChart = async () => {
  try {
    const data = await getPredictComparison({ limit: 20 })

    if (!charts.predict) {
      charts.predict = echarts.init(predictChart.value)
    }

    const titles = data.data.map(item => item.title)
    const actualData = data.data.map(item => item.actual)
    const predictedData = data.data.map(item => item.predicted)

    const option = {
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
          formatter: (value) => {
            return value.length > 8 ? value.substring(0, 8) + '...' : value
          }
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
    }

    charts.predict.setOption(option)
  } catch (error) {
    console.error('加载预测对比图失败:', error)
  }
}

// 初始化
onMounted(() => {
  loadChart(currentChart.value)

  // 响应式
  window.addEventListener('resize', () => {
    Object.values(charts).forEach(chart => chart?.resize())
  })
})

onUnmounted(() => {
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
  min-height: 600px;
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
  height: 500px;
}

:deep(.el-radio-button__inner) {
  padding: 12px 20px;
}

:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-left: var(--el-border-width);
  border-radius: var(--el-border-radius-base);
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: var(--el-border-radius-base);
}
</style>
