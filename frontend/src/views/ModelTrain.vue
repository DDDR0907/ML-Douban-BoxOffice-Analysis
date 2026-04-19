<template>
  <div class="model-train">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>模型训练</h3>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :xs="24" :lg="10">
          <div class="panel train-config">
            <h4>训练配置</h4>

            <el-form :model="trainConfig" label-width="110px">
              <el-form-item label="模型类型">
                <el-select v-model="trainConfig.model_type" placeholder="选择模型类型">
                  <el-option label="XGBoost" value="xgboost" />
                  <el-option label="线性回归" value="lr" />
                  <el-option label="全部模型" value="all" />
                </el-select>
              </el-form-item>

              <el-form-item label="测试集比例">
                <el-slider v-model="trainConfig.test_size" :min="0.1" :max="0.5" :step="0.05" show-input />
                <div class="helper-text">
                  训练集 {{ (1 - trainConfig.test_size).toFixed(2) }}，测试集 {{ trainConfig.test_size.toFixed(2) }}
                </div>
              </el-form-item>

              <el-form-item label="超参调优">
                <el-switch
                  v-model="trainConfig.tune_hyperparameters"
                  :disabled="trainConfig.model_type !== 'xgboost'"
                  active-text="开启"
                  inactive-text="关闭"
                />
                <div class="helper-text">仅 XGBoost 有效，开启后会增加训练耗时。</div>
              </el-form-item>

              <el-form-item label="交叉验证">
                <el-switch
                  v-model="trainConfig.cross_validation"
                  :disabled="trainConfig.model_type !== 'xgboost'"
                  active-text="开启"
                  inactive-text="关闭"
                />
                <div class="helper-text">当前后端默认对 XGBoost 执行 5 折验证。</div>
              </el-form-item>
            </el-form>

            <div class="action-buttons">
              <el-button
                type="primary"
                :loading="trainStatus.running"
                :disabled="!canStartTrain"
                @click="startTrain"
                size="large"
              >
                <el-icon><VideoPlay v-if="!trainStatus.running" /><Loading v-else /></el-icon>
                {{ trainStatus.running ? '训练中...' : '开始训练' }}
              </el-button>
              <el-button v-if="trainStatus.running" @click="stopTrain" size="large">
                <el-icon><VideoPause /></el-icon>
                停止训练
              </el-button>
            </div>
          </div>
        </el-col>

        <el-col :xs="24" :lg="14">
          <div class="panel train-status">
            <h4>训练状态</h4>

            <div v-if="trainStatus.running || trainStatus.progress > 0" class="progress-section">
              <el-progress
                :percentage="trainStatus.progress"
                :status="trainStatus.status"
                :stroke-width="20"
              >
                <span class="progress-text">{{ trainStatus.progress }}%</span>
              </el-progress>
              <p class="current-step">{{ trainStatus.currentStep || '等待状态更新...' }}</p>
            </div>

            <div v-else class="status-empty">
              <el-icon class="empty-icon"><Cpu /></el-icon>
              <p>配置参数后点击“开始训练”</p>
            </div>

            <div v-if="trainLogs.length" class="train-logs">
              <h5>训练日志</h5>
              <div class="log-content">
                <div v-for="(log, index) in trainLogs" :key="index" class="log-item">
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <div v-if="trainResult" class="train-result">
        <el-divider>训练结果</el-divider>

        <div v-if="trainResult.models?.length" class="result-panel">
          <h4>模型性能对比</h4>
          <el-table :data="modelComparisonData" style="width: 100%">
            <el-table-column prop="name" label="模型" />
            <el-table-column prop="train_r2" label="训练集 R2">
              <template #default="{ row }">
                {{ row.train_r2.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="test_r2" label="测试集 R2">
              <template #default="{ row }">
                <el-tag :type="row.test_r2 >= 0.7 ? 'success' : 'warning'">{{ row.test_r2.toFixed(4) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="test_rmse" label="测试集 RMSE">
              <template #default="{ row }">
                {{ row.test_rmse.toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-else class="result-panel">
          <el-row :gutter="20">
            <el-col :xs="24" :md="8">
              <div class="metric-card">
                <div class="metric-title">训练集 R2</div>
                <div class="metric-value">{{ singleResultMetrics.train_r2.toFixed(4) }}</div>
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="metric-card">
                <div class="metric-title">测试集 R2</div>
                <div class="metric-value" :class="{ 'metric-good': singleResultMetrics.test_r2 >= 0.7 }">
                  {{ singleResultMetrics.test_r2.toFixed(4) }}
                </div>
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="metric-card">
                <div class="metric-title">测试集 RMSE</div>
                <div class="metric-value">{{ singleResultMetrics.test_rmse.toFixed(2) }}</div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="20" class="metric-row">
            <el-col :xs="24" :md="12">
              <div class="metric-card">
                <div class="metric-title">测试集 MAE</div>
                <div class="metric-value">{{ singleResultMetrics.test_mae.toFixed(2) }}</div>
              </div>
            </el-col>
            <el-col :xs="24" :md="12">
              <div class="metric-card">
                <div class="metric-title">模型版本</div>
                <div class="metric-value metric-secondary">{{ trainResult.version || '-' }}</div>
              </div>
            </el-col>
          </el-row>

          <div v-if="featureImportanceList.length" class="feature-section">
            <h5>本次训练特征重要性</h5>
            <div class="feature-list">
              <div
                v-for="item in featureImportanceList"
                :key="item.name"
                class="feature-item"
              >
                <span class="feature-name">{{ item.name }}</span>
                <el-progress
                  :percentage="item.value"
                  :stroke-width="10"
                  :show-text="true"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="compare-section">
        <el-divider>模型解释对比</el-divider>
        <div class="panel">
          <div class="section-title-row">
            <h4>多模型特征重要性对比</h4>
            <el-button size="small" @click="loadMultiModelFeatureChart">刷新图表</el-button>
          </div>
          <div ref="multiModelFeatureChart" class="compare-chart"></div>
        </div>
      </div>

      <el-divider>已训练模型</el-divider>
      <div class="model-list">
        <el-table :data="modelList" style="width: 100%" v-loading="loadingModels">
          <el-table-column prop="model_type" label="模型类型" width="120">
            <template #default="{ row }">
              <el-tag>{{ row.model_type.toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '未启用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="viewModelMetrics(row)">查看指标</el-button>
              <el-button
                size="small"
                type="primary"
                v-if="!row.is_active"
                @click="enableModel(row)"
              >
                启用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="metricsDialog" title="模型详细指标" width="680px">
      <div v-if="currentModelMetrics">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="模型类型">
            {{ currentModelMetrics.model_type?.toUpperCase() }}
          </el-descriptions-item>
          <el-descriptions-item label="R2 分数">
            {{ (currentModelMetrics.metrics?.r2_score || 0).toFixed(4) }}
          </el-descriptions-item>
          <el-descriptions-item label="RMSE">
            {{ (currentModelMetrics.metrics?.rmse || 0).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="MAE">
            {{ (currentModelMetrics.metrics?.mae || 0).toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="MAPE">
            {{ (currentModelMetrics.metrics?.mape || 0).toFixed(2) }}%
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>特征重要性</el-divider>
        <div class="feature-list">
          <div
            v-for="item in dialogFeatureImportanceList"
            :key="item.name"
            class="feature-item"
          >
            <span class="feature-name">{{ item.name }}</span>
            <el-progress :percentage="item.value" :stroke-width="8" />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getMultiModelFeatureImportance } from '@/api/visualize'
import { getModelList, getModelMetrics, getTrainStatus, selectModel, startTrain as startTrainAPI } from '@/api/model'

const trainConfig = ref({
  model_type: 'xgboost',
  test_size: 0.3,
  tune_hyperparameters: true,
  cross_validation: true
})

const trainStatus = ref({
  running: false,
  progress: 0,
  currentStep: '',
  status: null
})

const trainLogs = ref([])
const trainResult = ref(null)
const modelList = ref([])
const loadingModels = ref(false)
const metricsDialog = ref(false)
const currentModelMetrics = ref(null)

let trainTimer = null
let multiModelFeatureInstance = null
let resizeHandler = null

const multiModelFeatureChart = ref(null)

const canStartTrain = computed(() => !trainStatus.value.running)

const modelComparisonData = computed(() => {
  const metrics = trainResult.value?.metrics || {}
  return Object.entries(metrics).map(([key, value]) => ({
    name: key === 'xgboost' ? 'XGBoost' : key === 'lr' ? '线性回归' : key,
    train_r2: Number(value.train_r2 || 0),
    test_r2: Number(value.test_r2 || 0),
    test_rmse: Number(value.test_rmse || 0)
  }))
})

const singleResultMetrics = computed(() => {
  const metrics = trainResult.value?.metrics || {}
  return {
    train_r2: Number(metrics.train_r2 || 0),
    test_r2: Number(metrics.test_r2 || 0),
    test_rmse: Number(metrics.test_rmse || 0),
    test_mae: Number(metrics.test_mae || 0)
  }
})

const featureImportanceList = computed(() => toFeatureImportanceList(trainResult.value?.feature_importance))
const dialogFeatureImportanceList = computed(() => toFeatureImportanceList(currentModelMetrics.value?.feature_importance))

function formatFeatureName(name) {
  return String(name)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
}

function toFeatureImportanceList(rawImportance) {
  return Object.entries(rawImportance || {})
    .map(([name, value]) => ({
      name: formatFeatureName(name),
      value: Math.round(Number(value || 0) * 100)
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12)
}

function addLog(message) {
  trainLogs.value.push({
    time: new Date().toLocaleTimeString(),
    message
  })
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
    series: []
  }, true)
}

async function startTrain() {
  try {
    const result = await startTrainAPI({
      model_type: trainConfig.value.model_type,
      test_size: trainConfig.value.test_size,
      tune_hyperparameters: trainConfig.value.tune_hyperparameters,
      cross_validation: trainConfig.value.cross_validation
    })

    trainStatus.value.running = true
    trainStatus.value.progress = 0
    trainStatus.value.currentStep = '任务已创建，等待训练启动...'
    trainStatus.value.status = null
    trainLogs.value = []
    trainResult.value = null
    addLog('训练任务已启动')

    trainTimer = setInterval(() => {
      checkTrainStatus(result.id)
    }, 2000)

    ElMessage.success('训练任务已启动')
  } catch (error) {
    ElMessage.error('启动训练失败')
  }
}

async function checkTrainStatus(taskId) {
  try {
    const status = await getTrainStatus(taskId)

    trainStatus.value.progress = status.progress || 0
    trainStatus.value.currentStep = status.current_step || ''

    if (status.progress >= 20 && trainLogs.value.length < 2) addLog('正在加载数据...')
    if (status.progress >= 45 && trainLogs.value.length < 3) addLog('正在执行模型训练...')
    if (status.progress >= 75 && trainLogs.value.length < 4) addLog('正在评估训练结果...')

    if (status.status === 'success') {
      trainStatus.value.running = false
      trainStatus.value.status = 'success'
      clearInterval(trainTimer)
      addLog('训练完成')
      trainResult.value = status.result || null
      ElMessage.success('训练完成')
      await Promise.all([loadModelList(), loadMultiModelFeatureChart()])
    } else if (status.status === 'failed') {
      trainStatus.value.running = false
      trainStatus.value.status = 'exception'
      clearInterval(trainTimer)
      addLog(`训练失败: ${status.error_msg || '未知错误'}`)
      ElMessage.error('训练失败')
    }
  } catch (error) {
    console.error('获取训练状态失败:', error)
  }
}

function stopTrain() {
  trainStatus.value.running = false
  trainStatus.value.status = 'warning'
  if (trainTimer) {
    clearInterval(trainTimer)
  }
  addLog('训练轮询已停止')
}

async function loadModelList() {
  loadingModels.value = true
  try {
    const data = await getModelList()
    modelList.value = data.models || []
  } catch (error) {
    console.error('加载模型列表失败:', error)
  } finally {
    loadingModels.value = false
  }
}

async function loadMultiModelFeatureChart() {
  try {
    const data = await getMultiModelFeatureImportance(10)
    if (!multiModelFeatureInstance && multiModelFeatureChart.value) {
      multiModelFeatureInstance = echarts.init(multiModelFeatureChart.value)
    }
    if (!multiModelFeatureInstance) return

    const features = data.features || []
    const models = data.models || []

    if (!features.length || !models.length) {
      renderEmptyState(multiModelFeatureInstance, data.message || '暂无多模型特征重要性对比数据')
      return
    }

    multiModelFeatureInstance.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: models.map(model => model.model_name)
      },
      grid: {
        left: '18%',
        right: '6%',
        bottom: '12%'
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

async function viewModelMetrics(model) {
  try {
    currentModelMetrics.value = await getModelMetrics(model.model_type)
    metricsDialog.value = true
  } catch (error) {
    ElMessage.error('加载模型指标失败')
  }
}

async function enableModel(model) {
  try {
    await selectModel(model.model_type)
    ElMessage.success('模型已启用')
    await loadModelList()
  } catch (error) {
    ElMessage.error('启用失败')
  }
}

function formatTime(timeValue) {
  if (!timeValue) return '-'
  return new Date(timeValue * 1000).toLocaleString('zh-CN')
}

onMounted(async () => {
  await Promise.all([loadModelList(), loadMultiModelFeatureChart()])
  resizeHandler = () => {
    multiModelFeatureInstance?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  if (trainTimer) {
    clearInterval(trainTimer)
  }
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  multiModelFeatureInstance?.dispose()
})
</script>

<style scoped>
.model-train {
  padding: 0;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
}

.panel {
  height: 100%;
  padding: 20px;
  background: #f8fafc;
  border-radius: 14px;
}

.train-config h4,
.train-status h4 {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #1f2937;
}

.helper-text {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.action-buttons {
  margin-top: 28px;
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.progress-section {
  padding: 20px;
  background: #fff;
  border-radius: 12px;
}

.progress-text {
  font-weight: 600;
}

.current-step {
  margin: 15px 0 0;
  text-align: center;
  color: #606266;
}

.status-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 18px;
  opacity: 0.35;
}

.train-logs {
  margin-top: 20px;
}

.train-logs h5 {
  margin: 0 0 10px;
  color: #475569;
}

.log-content {
  background: #111827;
  color: #86efac;
  padding: 14px;
  border-radius: 10px;
  max-height: 220px;
  overflow-y: auto;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
}

.log-item {
  margin-bottom: 6px;
}

.log-time {
  color: #93c5fd;
  margin-right: 8px;
}

.train-result,
.compare-section {
  margin-top: 28px;
}

.result-panel {
  background: #f8fafc;
  padding: 20px;
  border-radius: 14px;
}

.result-panel h4 {
  margin: 0 0 16px;
}

.metric-row {
  margin-top: 16px;
}

.metric-card {
  background: #fff;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

.metric-title {
  font-size: 14px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}

.metric-value.metric-good {
  color: #16a34a;
}

.metric-value.metric-secondary {
  font-size: 20px;
}

.feature-section {
  margin-top: 22px;
  background: #fff;
  padding: 18px;
  border-radius: 12px;
}

.feature-section h5 {
  margin: 0 0 14px;
}

.feature-list {
  margin-top: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.feature-name {
  width: 180px;
  font-size: 13px;
  color: #475569;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title-row h4 {
  margin: 0;
}

.compare-chart {
  width: 100%;
  height: 420px;
}

.model-list {
  margin-top: 18px;
}
</style>
