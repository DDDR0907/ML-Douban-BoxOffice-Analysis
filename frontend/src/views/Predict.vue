<template>
  <div class="predict">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>票房预测</h3>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 单个预测 -->
        <el-tab-pane label="单个预测" name="single">
          <el-row :gutter="20">
            <el-col :span="10">
              <el-form :model="predictForm" label-width="120px">
                <el-form-item label="预测方式">
                  <el-radio-group v-model="predictMethod">
                    <el-radio value="select">选择已有电影</el-radio>
                    <el-radio value="manual">手动输入</el-radio>
                  </el-radio-group>
                </el-form-item>

                <!-- 选择电影 -->
                <div v-if="predictMethod === 'select'">
                  <el-form-item label="选择电影">
                    <el-select
                      v-model="predictForm.movie_id"
                      filterable
                      remote
                      reserve-keyword
                      clearable
                      placeholder="输入电影名称搜索"
                      :remote-method="searchMovies"
                      :loading="searching"
                      :fit-input-width="true"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="movie in movieOptions"
                        :key="movie.id"
                        :label="movie.title"
                        :value="movie.id"
                      >
                        <span>{{ movie.title }}</span>
                        <span style="float: right; color: #8492a6; font-size: 13px">
                          {{ movie.release_year }}
                        </span>
                      </el-option>
                    </el-select>
                  </el-form-item>
                </div>

                <!-- 手动输入 -->
                <div v-else>
                  <el-form-item label="电影名称" required>
                    <el-input v-model="predictForm.title" placeholder="请输入电影名称" clearable />
                  </el-form-item>
                  <el-form-item label="豆瓣评分" required>
                    <el-input-number v-model="predictForm.rating" :min="0" :max="10" :step="0.1" :precision="1" controls-position="right" style="width: 100%" />
                  </el-form-item>
                  <el-form-item label="评分人数" required>
                    <el-input-number v-model="predictForm.rating_count" :min="0" :step="1" controls-position="right" style="width: 100%" />
                  </el-form-item>
                  <el-form-item label="想看人数">
                    <el-input-number v-model="predictForm.wish_count" :min="0" :step="1" controls-position="right" style="width: 100%" />
                  </el-form-item>
                  <el-form-item label="电影类型">
                    <el-select v-model="predictForm.type" placeholder="选择类型" clearable style="width: 100%">
                      <el-option label="剧情" value="剧情" />
                      <el-option label="喜剧" value="喜剧" />
                      <el-option label="动作" value="动作" />
                      <el-option label="科幻" value="科幻" />
                      <el-option label="爱情" value="爱情" />
                      <el-option label="动画" value="动画" />
                      <el-option label="悬疑" value="悬疑" />
                      <el-option label="战争" value="战争" />
                      <el-option label="犯罪" value="犯罪" />
                      <el-option label="纪录片" value="纪录片" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="上映年份">
                    <el-input-number v-model="predictForm.release_year" :min="2000" :max="2030" :step="1" controls-position="right" style="width: 100%" />
                  </el-form-item>
                  <el-form-item label="平均票价">
                    <el-input-number v-model="predictForm.avg_price" :min="0" :max="500" :step="0.1" :precision="1" controls-position="right" style="width: 100%" />
                  </el-form-item>
                </div>

                <el-form-item label="预测模型">
                  <el-select v-model="predictForm.model_type" placeholder="选择模型">
                    <el-option label="XGBoost" value="xgboost" />
                    <el-option label="线性回归" value="lr" />
                  </el-select>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" :loading="predicting" @click="doPredict">
                    <el-icon><TrendCharts /></el-icon>
                    开始预测
                  </el-button>
                  <el-button @click="resetForm">重置</el-button>
                </el-form-item>
              </el-form>
            </el-col>

            <el-col :span="14">
              <!-- 预测结果 -->
              <div v-if="predictResult" class="result-panel">
                <h3>预测结果</h3>

                <div class="result-card">
                  <div class="result-main">
                    <div class="result-value">
                      {{ Math.abs(predictResult.predicted_box_office_wan || 0).toLocaleString() }}
                    </div>
                    <div class="result-unit">万元</div>
                  </div>
                  <div class="result-sub">
                    <div class="result-sub-item">
                      <span class="label">置信区间:</span>
                      <span class="value">
                        {{ Math.abs(predictResult.confidence_lower_wan || 0).toLocaleString() }} -
                        {{ Math.abs(predictResult.confidence_upper_wan || 0).toLocaleString() }} 万元
                      </span>
                    </div>
                    <div class="result-sub-item">
                      <span class="label">使用模型:</span>
                      <span class="value">{{ predictResult.model_type?.toUpperCase() }}</span>
                    </div>
                  </div>
                </div>

                <!-- 特征重要性 -->
                <div v-if="predictResult.feature_importance" class="feature-importance">
                  <h4>特征贡献度</h4>
                  <div class="feature-list">
                    <div
                      v-for="(value, key) in sortedFeatureImportance"
                      :key="key"
                      class="feature-item"
                    >
                      <div class="feature-info">
                        <span class="feature-name">{{ getFeatureDisplayName(key) }}</span>
                        <span class="feature-value">{{ (value * 100).toFixed(1) }}%</span>
                      </div>
                      <el-progress
                        :percentage="Math.round(value * 100)"
                        :stroke-width="12"
                        :show-text="false"
                        :color="getFeatureColor(value)"
                      />
                    </div>
                  </div>
                </div>

                <!-- 实际对比 -->
                <div v-if="predictResult.actual_box_office_wan" class="comparison">
                  <h4>实际对比</h4>
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <div class="compare-item">
                        <span class="label">预测票房:</span>
                        <span class="value">{{ predictResult.predicted_box_office_wan?.toLocaleString() }} 万</span>
                      </div>
                    </el-col>
                    <el-col :span="12">
                      <div class="compare-item">
                        <span class="label">实际票房:</span>
                        <span class="value">{{ predictResult.actual_box_office_wan?.toLocaleString() }} 万</span>
                      </div>
                    </el-col>
                  </el-row>
                  <el-row :gutter="20" style="margin-top: 10px">
                    <el-col :span="12">
                      <div class="compare-item">
                        <span class="label">误差:</span>
                        <span class="value" :class="{'error-high': predictResult.error_percentage > 20}">
                          {{ predictResult.error_wan?.toLocaleString() }} 万
                          ({{ predictResult.error_percentage?.toFixed(1) }}%)
                        </span>
                      </div>
                    </el-col>
                  </el-row>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-else class="empty-result">
                <el-icon class="empty-icon"><TrendCharts /></el-icon>
                <p>请填写信息后点击预测</p>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 批量预测 -->
        <el-tab-pane label="批量预测" name="batch">
          <el-upload
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleBatchFileChange"
            accept=".xlsx,.xls"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将包含电影信息的Excel文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                文件需包含: 电影名称、评分、评分人数等字段
              </div>
            </template>
          </el-upload>

          <div v-if="batchResults.length > 0" class="batch-results">
            <el-divider>批量预测结果</el-divider>
            <el-alert
              :title="`成功预测 ${batchSuccessCount} 条，失败 ${batchFailCount} 条`"
              :type="batchFailCount > 0 ? 'warning' : 'success'"
              :closable="false"
              style="margin-bottom: 20px"
            />

            <el-table :data="batchResults" style="width: 100%" max-height="500">
              <el-table-column prop="title" label="电影名称" />
              <el-table-column prop="predicted_box_office_wan" label="预测票房(万元)">
                <template #default="{ row }">
                  {{ Math.abs(row.predicted_box_office_wan || 0).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="confidence_lower_wan" label="下限(万元)">
                <template #default="{ row }">
                  {{ Math.abs(row.confidence_lower_wan || 0).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="confidence_upper_wan" label="上限(万元)">
                <template #default="{ row }">
                  {{ Math.abs(row.confidence_upper_wan || 0).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column prop="model_type" label="模型" width="100" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.error" type="danger">失败</el-tag>
                  <el-tag v-else type="success">成功</el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div class="action-buttons">
              <el-button @click="exportBatchResults">导出结果</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 预测历史 -->
        <el-tab-pane label="预测历史" name="history">
          <el-table :data="historyList" style="width: 100%" v-loading="loadingHistory">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="title" label="电影名称" min-width="200">
              <template #default="{ row }">
                {{ row.movie?.title || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="predicted_box_office_wan" label="预测票房(万元)">
              <template #default="{ row }">
                {{ Math.abs(row.predicted_box_office_wan || 0).toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column prop="model_type" label="模型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.model_type?.toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="预测时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" @click="viewHistoryDetail(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="historyPagination.page"
            v-model:page-size="historyPagination.pageSize"
            :total="historyPagination.total"
            layout="total, prev, pager, next"
            @current-change="loadHistory"
            style="margin-top: 20px"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { predictSingle, predictBatch, getPredictionHistory } from '@/api/predict'
import { getMovies } from '@/api/data'

const activeTab = ref('single')
const predictMethod = ref('select')
const predicting = ref(false)

// 预测表单
const predictForm = ref({
  movie_id: null,
  title: '',
  rating: null,
  rating_count: null,
  wish_count: null,
  type: '',
  release_year: null,
  avg_price: null,
  model_type: 'xgboost'
})

// 预测结果
const predictResult = ref(null)

// 计算排序后的特征重要性
const sortedFeatureImportance = computed(() => {
  if (!predictResult.value?.feature_importance) return {}
  const importance = predictResult.value.feature_importance
  return Object.fromEntries(
    Object.entries(importance).sort(([, a], [, b]) => b - a)
  )
})

// 特征名称映射
const featureNameMap = {
  'rating': '豆瓣评分',
  'rating_count': '评分人数',
  'wish_count': '想看人数',
  'type': '电影类型',
  'release_year': '上映年份',
  'avg_price': '平均票价',
  'per_session_attendance': '场均人次',
  'box_office_wan': '票房(万元)'
}

// 获取特征显示名称
const getFeatureDisplayName = (key) => {
  return featureNameMap[key] || key
}

// 获取特征颜色
const getFeatureColor = (value) => {
  const percentage = value * 100
  if (percentage >= 30) return '#f56c6c' // 红色 - 高贡献
  if (percentage >= 20) return '#e6a23c' // 橙色 - 中高贡献
  if (percentage >= 10) return '#409eff' // 蓝色 - 中等贡献
  return '#67c23a' // 绿色 - 低贡献
}

// 搜索电影
const searching = ref(false)
const movieOptions = ref([])

// 批量预测
const batchResults = ref([])

// 历史记录
const loadingHistory = ref(false)
const historyList = ref([])
const historyPagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 搜索电影
const searchMovies = async (query) => {
  if (!query) return

  searching.value = true
  try {
    const data = await getMovies({
      title: query,
      page: 1,
      page_size: 10
    })
    movieOptions.value = data.data || []
  } catch (error) {
    console.error('搜索失败')
  } finally {
    searching.value = false
  }
}

// 执行预测
const doPredict = async () => {
  // 验证
  if (predictMethod.value === 'select') {
    if (!predictForm.value.movie_id) {
      ElMessage.warning('请选择电影')
      return
    }
  } else {
    if (!predictForm.value.title || !predictForm.value.rating || !predictForm.value.rating_count) {
      ElMessage.warning('请填写必填项')
      return
    }
  }

  predicting.value = true
  try {
    const params = predictMethod.value === 'select'
      ? { movie_id: predictForm.value.movie_id, model_type: predictForm.value.model_type }
      : { ...predictForm.value, model_type: predictForm.value.model_type }

    const result = await predictSingle(params)
    predictResult.value = result
    ElMessage.success('预测成功')
    loadHistory()
  } catch (error) {
    ElMessage.error('预测失败')
  } finally {
    predicting.value = false
  }
}

// 重置表单
const resetForm = () => {
  predictForm.value = {
    movie_id: null,
    title: '',
    rating: null,
    rating_count: null,
    wish_count: null,
    type: '',
    release_year: null,
    avg_price: null,
    model_type: 'xgboost'
  }
  predictResult.value = null
}

// 批量预测文件变化
const handleBatchFileChange = async (file) => {
  try {
    const formData = new FormData()
    formData.append('file', file.raw)

    const results = await predictBatch(file.raw, 'xgboost')
    batchResults.value = results.results || []
    ElMessage.success(`批量预测完成，共 ${results.total} 条`)
  } catch (error) {
    ElMessage.error('批量预测失败')
  }
}

// 批量成功数
const batchSuccessCount = ref(0)
const batchFailCount = ref(0)

// 加载历史记录
const loadHistory = async () => {
  loadingHistory.value = true
  try {
    const data = await getPredictionHistory({
      page: historyPagination.value.page,
      page_size: historyPagination.value.pageSize
    })
    historyList.value = data.data || []
    historyPagination.value.total = data.total || 0
  } catch (error) {
    console.error('加载历史失败')
  } finally {
    loadingHistory.value = false
  }
}

// 查看历史详情
const viewHistoryDetail = (row) => {
  predictResult.value = row
  activeTab.value = 'single'
}

// 导出批量结果
const exportBatchResults = () => {
  // TODO: 实现导出功能
  ElMessage.info('导出功能开发中')
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.predict {
  padding: 0;
}

.result-panel {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.result-panel h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #303133;
}

.result-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 12px;
  text-align: center;
  margin-bottom: 20px;
}

.result-main {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 10px;
}

.result-value {
  font-size: 48px;
  font-weight: 700;
}

.result-unit {
  font-size: 18px;
  opacity: 0.9;
}

.result-sub {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(255,255,255,0.2);
}

.result-sub-item {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 5px;
}

.result-sub-item .label {
  opacity: 0.8;
}

.feature-importance {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.feature-importance h4 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.feature-item {
  margin-bottom: 15px;
}

.feature-item:last-child {
  margin-bottom: 0;
}

.feature-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.feature-name {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.feature-value {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}

.comparison {
  margin-top: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.comparison h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
}

.compare-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}

.compare-item .label {
  color: #909399;
}

.compare-item .value {
  font-weight: 600;
  color: #303133;
}

.compare-item .value.error-high {
  color: #f56c6c;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.3;
}

.batch-results {
  margin-top: 30px;
}

.action-buttons {
  margin-top: 20px;
  text-align: center;
}
</style>
