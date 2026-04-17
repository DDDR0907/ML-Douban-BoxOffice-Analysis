<template>
  <div class="model-train">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>模型训练</h3>
        </div>
      </template>

      <el-row :gutter="20">
        <!-- 左侧：训练配置 -->
        <el-col :span="10">
          <div class="train-config">
            <h4>训练配置</h4>

            <el-form :model="trainConfig" label-width="120px">
              <el-form-item label="模型类型">
                <el-select v-model="trainConfig.model_type" placeholder="选择模型类型">
                  <el-option label="XGBoost" value="xgboost">
                    <div>
                      <span>XGBoost</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">
                        高精度，适合复杂数据
                      </span>
                    </div>
                  </el-option>
                  <el-option label="线性回归" value="lr">
                    <div>
                      <span>线性回归</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">
                        基准模型，快速训练
                      </span>
                    </div>
                  </el-option>
                  <el-option label="全部模型" value="all">
                    <div>
                      <span>全部模型</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">
                        训练所有模型并对比
                      </span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="测试集比例">
                <el-slider v-model="trainConfig.test_size" :min="0.1" :max="0.5" :step="0.05" show-input />
                <span style="font-size: 12px; color: #909399">
                  训练集: {{ (1 - trainConfig.test_size).toFixed(2) }} | 测试集: {{ trainConfig.test_size.toFixed(2) }}
                </span>
              </el-form-item>

              <el-form-item label="超参数调优">
                <el-switch
                  v-model="trainConfig.tune_hyperparameters"
                  :disabled="trainConfig.model_type !== 'xgboost'"
                  active-text="开启"
                  inactive-text="关闭"
                />
                <div style="font-size: 12px; color: #909399; margin-top: 5px">
                  开启后将自动搜索最优参数，训练时间会延长
                </div>
              </el-form-item>

              <el-form-item label="交叉验证">
                <el-switch
                  v-model="trainConfig.cross_validation"
                  :disabled="trainConfig.model_type !== 'xgboost'"
                  active-text="开启"
                  inactive-text="关闭"
                />
                <div style="font-size: 12px; color: #909399; margin-top: 5px">
                  5折交叉验证，评估模型稳定性
                </div>
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
                <el-icon><VideoPlay v-if="!trainStatus.running" />
                <Loading v-else /></el-icon>
                {{ trainStatus.running ? '训练中...' : '开始训练' }}
              </el-button>
              <el-button v-if="trainStatus.running" @click="stopTrain" size="large">
                <el-icon><VideoPause /></el-icon>
                停止训练
              </el-button>
            </div>
          </div>
        </el-col>

        <!-- 右侧：训练状态 -->
        <el-col :span="14">
          <div class="train-status">
            <h4>训练状态</h4>

            <div v-if="trainStatus.running || trainStatus.progress > 0" class="progress-section">
              <el-progress
                :percentage="trainStatus.progress"
                :status="trainStatus.status"
                :stroke-width="20"
              >
                <span class="progress-text">{{ trainStatus.progress }}%</span>
              </el-progress>
              <p class="current-step">{{ trainStatus.currentStep }}</p>
            </div>

            <div v-else class="status-empty">
              <el-icon class="empty-icon"><Cpu /></el-icon>
              <p>配置参数后点击"开始训练"</p>
            </div>

            <!-- 训练日志 -->
            <div v-if="trainLogs.length > 0" class="train-logs">
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

      <!-- 训练结果 -->
      <div v-if="trainResult" class="train-result">
        <el-divider>训练结果</el-divider>

        <!-- 模型对比 -->
        <div v-if="trainResult.models" class="model-comparison">
          <h4>模型性能对比</h4>
          <el-table :data="modelComparisonData" style="width: 100%">
            <el-table-column prop="name" label="模型" />
            <el-table-column prop="r2" label="R² 分数">
              <template #default="{ row }">
                <el-tag :type="row.r2 > 0.7 ? 'success' : 'warning'">{{ row.r2.toFixed(4) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rmse" label="RMSE">
              <template #default="{ row }">
                {{ row.rmse?.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="mae" label="MAE">
              <template #default="{ row }">
                {{ row.mae?.toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 单个模型结果 -->
        <div v-else class="single-result">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="metric-card">
                <div class="metric-title">训练集 R²</div>
                <div class="metric-value">{{ trainResult.train_r2?.toFixed(4) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="metric-card">
                <div class="metric-title">测试集 R²</div>
                <div class="metric-value" :class="{'metric-good': trainResult.test_r2 > 0.7}">
                  {{ trainResult.test_r2?.toFixed(4) }}
                </div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20" style="margin-top: 15px">
            <el-col :span="12">
              <div class="metric-card">
                <div class="metric-title">测试集 RMSE</div>
                <div class="metric-value">{{ trainResult.test_rmse?.toFixed(2) }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="metric-card">
                <div class="metric-title">测试集 MAE</div>
                <div class="metric-value">{{ trainResult.test_mae?.toFixed(2) }}</div>
              </div>
            </el-col>
          </el-row>

          <!-- 特征重要性 -->
          <div v-if="trainResult.feature_importance" class="feature-section">
            <h5>特征重要性</h5>
            <div class="feature-list">
              <div
                v-for="(value, key) in trainResult.feature_importance"
                :key="key"
                class="feature-item"
              >
                <span class="feature-name">{{ key }}</span>
                <el-progress
                  :percentage="Math.round(value * 100)"
                  :stroke-width="10"
                  :show-text="true"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模型列表 -->
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
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '未启用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="viewModelMetrics(row)">查看指标</el-button>
              <el-button
                size="small"
                type="primary"
                v-if="!row.is_active"
                @click="enableModel(row.id)"
              >
                启用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 模型指标对话框 -->
    <el-dialog v-model="metricsDialog" title="模型详细指标" width="600px">
      <div v-if="currentModelMetrics">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="模型类型">
            {{ currentModelMetrics.model_type?.toUpperCase() }}
          </el-descriptions-item>
          <el-descriptions-item label="R² 分数">
            {{ currentModelMetrics.metrics?.r2_score?.toFixed(4) }}
          </el-descriptions-item>
          <el-descriptions-item label="RMSE">
            {{ currentModelMetrics.metrics?.rmse?.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="MAE">
            {{ currentModelMetrics.metrics?.mae?.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="MAPE">
            {{ currentModelMetrics.metrics?.mape?.toFixed(2) }}%
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>特征重要性</el-divider>
        <div class="feature-list">
          <div
            v-for="(value, key) in currentModelMetrics.feature_importance"
            :key="key"
            class="feature-item"
          >
            <span class="feature-name">{{ key }}</span>
            <el-progress
              :percentage="Math.round(value * 100)"
              :stroke-width="8"
            />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { startTrain as startTrainAPI, getTrainStatus, getModelList, selectModel, getModelMetrics } from '@/api/model'

// 训练配置
const trainConfig = ref({
  model_type: 'xgboost',
  test_size: 0.3,
  tune_hyperparameters: true,
  cross_validation: true
})

// 训练状态
const trainStatus = ref({
  running: false,
  progress: 0,
  currentStep: '',
  status: null
})

// 训练日志
const trainLogs = ref([])

// 训练结果
const trainResult = ref(null)

// 模型列表
const modelList = ref([])
const loadingModels = ref(false)

// 模型指标对话框
const metricsDialog = ref(false)
const currentModelMetrics = ref(null)

let trainTimer = null

// 是否可以开始训练
const canStartTrain = computed(() => {
  return !trainStatus.value.running
})

// 模型对比数据
const modelComparisonData = computed(() => {
  if (!trainResult.value?.models) return []

  const metrics = trainResult.value.metrics || {}
  return Object.entries(metrics).map(([key, value]) => ({
    name: key === 'xgboost' ? 'XGBoost' : key === 'lr' ? '线性回归' : key,
    r2: value['R²'] || 0,
    rmse: value.RMSE || 0,
    mae: value.MAE || 0
  }))
})

// 开始训练
const startTrain = async () => {
  try {
    const result = await startTrainAPI({
      model_type: trainConfig.value.model_type,
      test_size: trainConfig.value.test_size
    })

    trainStatus.value.running = true
    trainStatus.value.progress = 0
    addLog('训练任务已启动')

    // 开始轮询状态
    trainTimer = setInterval(() => {
      checkTrainStatus(result.id)
    }, 2000)

    ElMessage.success('训练任务已启动')
  } catch (error) {
    ElMessage.error('启动训练失败')
  }
}

// 检查训练状态
const checkTrainStatus = async (taskId) => {
  try {
    const status = await getTrainStatus(taskId)

    trainStatus.value.progress = status.progress || 0
    trainStatus.value.currentStep = status.current_step || ''

    // 根据进度更新日志
    if (status.progress > 25 && trainLogs.value.length < 2) {
      addLog('正在加载数据...')
    }
    if (status.progress > 50 && trainLogs.value.length < 3) {
      addLog('正在训练模型...')
    }
    if (status.progress > 80 && trainLogs.value.length < 4) {
      addLog('正在评估模型...')
    }

    if (status.status === 'success') {
      trainStatus.value.running = false
      trainStatus.value.status = 'success'
      clearInterval(trainTimer)
      addLog('训练完成!')
      ElMessage.success('训练完成')

      // 加载结果
      trainResult.value = status.result_dict
      loadModelList()
    } else if (status.status === 'failed') {
      trainStatus.value.running = false
      trainStatus.value.status = 'exception'
      clearInterval(trainTimer)
      addLog('训练失败: ' + status.error_msg)
      ElMessage.error('训练失败')
    }
  } catch (error) {
    console.error('获取状态失败')
  }
}

// 停止训练
const stopTrain = () => {
  trainStatus.value.running = false
  if (trainTimer) {
    clearInterval(trainTimer)
  }
  addLog('训练已停止')
}

// 添加日志
const addLog = (message) => {
  trainLogs.value.push({
    time: new Date().toLocaleTimeString(),
    message
  })
}

// 加载模型列表
const loadModelList = async () => {
  loadingModels.value = true
  try {
    const data = await getModelList()
    modelList.value = data.models || []
  } catch (error) {
    console.error('加载模型列表失败')
  } finally {
    loadingModels.value = false
  }
}

// 查看模型指标
const viewModelMetrics = async (model) => {
  try {
    const metrics = await getModelMetrics(model.model_type)
    currentModelMetrics.value = metrics
    metricsDialog.value = true
  } catch (error) {
    ElMessage.error('加载指标失败')
  }
}

// 启用模型
const enableModel = async (modelId) => {
  try {
    await selectModel(modelId)
    ElMessage.success('模型已启用')
    loadModelList()
  } catch (error) {
    ElMessage.error('启用失败')
  }
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  loadModelList()
})
</script>

<style scoped>
.model-train {
  padding: 0;
}

.train-config, .train-status {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  height: 100%;
}

.train-config h4, .train-status h4 {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #303133;
}

.action-buttons {
  margin-top: 30px;
  text-align: center;
}

.progress-section {
  padding: 20px;
  background: white;
  border-radius: 8px;
}

.current-step {
  margin-top: 15px;
  text-align: center;
  color: #606266;
  font-size: 14px;
}

.status-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.3;
}

.train-logs {
  margin-top: 20px;
}

.train-logs h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #606266;
}

.log-content {
  background: #303133;
  color: #67c23a;
  padding: 15px;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-item {
  margin-bottom: 5px;
}

.log-time {
  color: #909399;
  margin-right: 10px;
}

.train-result {
  margin-top: 30px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.metric-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.metric-value.metric-good {
  color: #67c23a;
}

.feature-section {
  margin-top: 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
}

.feature-section h5 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #606266;
}

.feature-list {
  margin-top: 10px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 12px;
}

.feature-name {
  width: 150px;
  font-size: 13px;
  color: #606266;
}

.model-list {
  margin-top: 20px;
}

.model-comparison {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}

.model-comparison h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
}

.single-result {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}
</style>
