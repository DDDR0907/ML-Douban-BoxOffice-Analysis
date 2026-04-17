<template>
  <div class="data-manage">
    <!-- 选项卡 -->
    <el-card class="card-tabs">
      <el-radio-group v-model="activeTab" size="large">
        <el-radio-button value="crawl">
          <el-icon><Connection /></el-icon>
          爬虫采集
        </el-radio-button>
        <el-radio-button value="upload">
          <el-icon><Upload /></el-icon>
          文件上传
        </el-radio-button>
        <el-radio-button value="list">
          <el-icon><List /></el-icon>
          数据列表
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- 爬虫采集 -->
    <div v-show="activeTab === 'crawl'" class="tab-content">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>豆瓣电影数据爬取</h3>
          </div>
        </template>

        <el-form :model="crawlConfig" label-width="120px">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="年份范围">
                <el-select v-model="crawlConfig.yearStart" placeholder="起始年份" style="width: 120px">
                  <el-option v-for="y in years" :key="y" :label="y" :value="y" />
                </el-select>
                <span style="margin: 0 10px">至</span>
                <el-select v-model="crawlConfig.yearEnd" placeholder="结束年份" style="width: 120px">
                  <el-option v-for="y in years" :key="y" :label="y" :value="y" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="最低评分">
                <el-slider v-model="crawlConfig.minRating" :min="0" :max="10" :step="0.5" show-input />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="最大爬取数">
            <el-input-number v-model="crawlConfig.maxMovies" :min="100" :max="10000" :step="100" />
          </el-form-item>
        </el-form>

        <div class="action-buttons">
          <el-button type="primary" :loading="crawlStatus.running" @click="startCrawl" :disabled="crawlStatus.running">
            <el-icon><VideoPlay /></el-icon>
            {{ crawlStatus.running ? '爬取中...' : '开始爬取' }}
          </el-button>
          <el-button v-if="crawlStatus.running" @click="stopCrawl">
            <el-icon><VideoPause /></el-icon>
            停止爬取
          </el-button>
        </div>

        <!-- 爬取进度 -->
        <div v-if="crawlStatus.running || crawlStatus.progress > 0" class="progress-wrapper">
          <el-progress :percentage="crawlStatus.progress" :status="crawlStatus.status" />
          <p class="progress-text">{{ crawlStatus.currentStep }}</p>
        </div>

        <!-- 爬取历史 -->
        <el-divider>爬取历史</el-divider>
        <el-table :data="crawlHistory" style="width: 100%">
          <el-table-column prop="id" label="任务ID" width="80" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="config_dict" label="配置" width="300">
            <template #default="{ row }">
              <el-tag v-if="row.config_dict" size="small">
                {{ row.config_dict.year_start }}-{{ row.config_dict.year_end }}年 |
                评分≥{{ row.config_dict.min_rating }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="progress" label="进度" width="120">
            <template #default="{ row }">
              <el-progress :percentage="row.progress || 0" :stroke-width="6" />
            </template>
          </el-table-column>
          <el-table-column prop="result_dict" label="结果">
            <template #default="{ row }">
              <span v-if="row.result_dict">
                爬取 {{ row.result_dict.total_crawled }} 条，
                保存 {{ row.result_dict.saved_count }} 条
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 文件上传 -->
    <div v-show="activeTab === 'upload'" class="tab-content">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>Excel文件上传</h3>
            <el-button size="small" @click="downloadTemplate">
              <el-icon><Download /></el-icon>
              下载模板
            </el-button>
          </div>
        </template>

        <!-- 上传区域 -->
        <el-upload
          drag
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          accept=".xlsx,.xls,.csv"
          :limit="1"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将Excel/CSV文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持.xlsx、.xls、.csv格式，文件大小不超过50MB
            </div>
          </template>
        </el-upload>

        <!-- 文件预览 -->
        <div v-if="previewData.length > 0" class="preview-section">
          <el-divider>数据预览（前10条）</el-divider>
          <el-alert
            title="请确认字段映射后点击导入"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            共 {{ totalRows }} 条数据
          </el-alert>

          <el-table :data="previewData" border max-height="250" :cell-style="{ padding: '4px 0' }" :header-cell-style="{ padding: '8px 0' }" size="small">
            <el-table-column
              v-for="col in columns"
              :key="col"
              :prop="col"
              :label="col"
              :min-width="120"
            />
          </el-table>

          <!-- 数据清理 -->
          <div v-if="cleanableColumns.length > 0" class="clean-section">
            <el-divider>数据清理（可选）</el-divider>

            <el-alert
              type="info"
              :closable="false"
              style="margin-bottom: 15px"
            >
              以下列数据格式需要清理，点击"清理"按钮自动转换格式
            </el-alert>

            <el-table :data="cleanableColumns" border size="small">
              <el-table-column prop="column" label="列名" width="150" />
              <el-table-column prop="sample" label="示例数据" min-width="200">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.sample }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="issue" label="问题" min-width="250" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag v-if="cleaningStatus[row.column] === 'cleaning'" type="warning" size="small">
                    清理中
                  </el-tag>
                  <el-tag v-else-if="cleaningStatus[row.column] === 'completed'" type="success" size="small">
                    已清理
                  </el-tag>
                  <el-tag v-else-if="cleaningStatus[row.column] === 'failed'" type="danger" size="small">
                    失败
                  </el-tag>
                  <el-tag v-else type="info" size="small">
                    待清理
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row }">
                  <el-button
                    size="small"
                    type="primary"
                    @click="cleanColumn(row)"
                    :disabled="cleaningStatus[row.column] === 'cleaning'"
                    :loading="cleaningStatus[row.column] === 'cleaning'"
                  >
                    {{ cleaningStatus[row.column] === 'completed' ? '重新清理' : '清理' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="cleanableColumns.length > 1" style="text-align: center; margin-top: 15px">
              <el-button type="success" @click="cleanAllColumns">
                <el-icon><Check /></el-icon>
                一键清理全部
              </el-button>
            </div>
          </div>

          <!-- 字段映射 -->
          <el-divider>字段映射</el-divider>
          <el-form :model="fieldMapping" label-width="120px">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="电影名称">
                  <el-select v-model="fieldMapping.title" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="票房(万元)">
                  <el-select v-model="fieldMapping.box_office_wan" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="上映年份">
                  <el-select v-model="fieldMapping.release_year" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="平均票价">
                  <el-select v-model="fieldMapping.avg_price" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="场均人次">
                  <el-select v-model="fieldMapping.per_session_attendance" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="排名">
                  <el-select v-model="fieldMapping.ranking" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item label="电影类型">
                  <el-select v-model="fieldMapping.type" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="豆瓣评分">
                  <el-select v-model="fieldMapping.rating" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="评分人数">
                  <el-select v-model="fieldMapping.rating_count" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="想看人数">
                  <el-select v-model="fieldMapping.wish_count" placeholder="选择对应列">
                    <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <div class="action-buttons">
            <el-button type="primary" :loading="importing" @click="confirmImport">
              <el-icon><Select /></el-icon>
              确认导入（共{{ totalRows }}条）
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 数据列表 -->
    <div v-show="activeTab === 'list'" class="tab-content">
      <el-card>
        <template #header>
          <div class="card-header">
            <h3>电影数据列表</h3>
            <div>
              <el-button size="small" @click="loadMovies">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button size="small" type="primary" @click="exportData">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
              <el-button size="small" type="danger" @click="deleteAllMovies">
                <el-icon><Delete /></el-icon>
                全部删除
              </el-button>
            </div>
          </div>
        </template>

        <!-- 搜索 -->
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="电影名称">
            <el-input v-model="searchForm.title" placeholder="输入电影名称" clearable style="width: 200px" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="searchForm.type" placeholder="选择类型" clearable style="width: 150px">
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
          <el-form-item>
            <el-button type="primary" @click="loadMovies">搜索</el-button>
            <el-button @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>

        <!-- 数据表格 -->
        <el-table :data="movieList" style="width: 100%" v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="title" label="电影名称" min-width="200" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="release_year" label="年份" width="80" />
          <el-table-column prop="rating" label="评分" width="80" />
          <el-table-column prop="box_office_wan" label="票房(万元)" width="120">
            <template #default="{ row }">
              {{ row.box_office_wan?.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column prop="data_source" label="来源" width="100">
            <template #default="{ row }">
              <el-tag :type="row.data_source === 'crawl' ? 'success' : 'warning'" size="small">
                {{ row.data_source === 'crawl' ? '爬虫' : '上传' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewDetail(row)">查看</el-button>
              <el-button size="small" type="danger" @click="deleteMovie(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadMovies"
          @current-change="loadMovies"
          style="margin-top: 20px; justify-content: center"
        />
      </el-card>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog" title="电影详情" width="600px">
      <el-descriptions v-if="currentMovie" :column="2" border>
        <el-descriptions-item label="电影名称">{{ currentMovie.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ currentMovie.type }}</el-descriptions-item>
        <el-descriptions-item label="上映年份">{{ currentMovie.release_year }}</el-descriptions-item>
        <el-descriptions-item label="豆瓣评分">{{ currentMovie.rating }}</el-descriptions-item>
        <el-descriptions-item label="评分人数">{{ currentMovie.rating_count }}</el-descriptions-item>
        <el-descriptions-item label="想看人数">{{ currentMovie.wish_count }}</el-descriptions-item>
        <el-descriptions-item label="票房(万元)">{{ currentMovie.box_office_wan?.toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="平均票价">{{ currentMovie.avg_price }}</el-descriptions-item>
        <el-descriptions-item label="数据来源">
          <el-tag :type="currentMovie.data_source === 'crawl' ? 'success' : 'warning'">
            {{ currentMovie.data_source === 'crawl' ? '爬虫' : '上传' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  startCrawl as apiStartCrawl,
  stopCrawl as apiStopCrawl,
  getCrawlStatus,
  getCrawlHistory
} from '@/api/crawl'
import { uploadFile, importData, getMovies, deleteMovie as apiDeleteMovie, downloadTemplate as apiDownloadTemplate, exportData as apiExportData, deleteAllMovies as apiDeleteAllMovies, cleanData } from '@/api/data'

const activeTab = ref('crawl')

// 爬虫配置
const years = ref([])
const crawlConfig = ref({
  yearStart: 2010,
  yearEnd: 2024,
  minRating: 5.0,
  maxMovies: 5000
})
const crawlStatus = ref({
  running: false,
  progress: 0,
  currentStep: '',
  status: null
})
const crawlHistory = ref([])
let crawlTimer = null

// 文件上传
const previewData = ref([])
const columns = ref([])
const totalRows = ref(0)
const fileId = ref('')
const fieldMapping = ref({
  title: '',
  box_office_wan: '',
  release_year: '',
  avg_price: '',
  per_session_attendance: '',
  ranking: '',
  type: '',
  rating: '',
  rating_count: '',
  wish_count: ''
})
const importing = ref(false)

// 数据清理
const cleanableColumns = ref([])
const cleaningStatus = ref({}) // { columnName: status }

// 数据列表
const loading = ref(false)
const movieList = ref([])
const searchForm = ref({
  title: '',
  type: ''
})
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 详情
const detailDialog = ref(false)
const currentMovie = ref(null)

// 初始化年份
onMounted(() => {
  const currentYear = new Date().getFullYear()
  for (let y = 2000; y <= currentYear; y++) {
    years.value.push(y)
  }
  loadCrawlHistory()
  loadMovies()
})

// 开始爬取
const startCrawl = async () => {
  try {
    const result = await apiStartCrawl({
      year_start: crawlConfig.value.yearStart,
      year_end: crawlConfig.value.yearEnd,
      min_rating: crawlConfig.value.minRating,
      max_movies: crawlConfig.value.maxMovies
    })

    crawlStatus.value.running = true
    crawlStatus.value.progress = 0

    // 开始轮询状态
    crawlTimer = setInterval(() => {
      checkCrawlStatus(result.id)
    }, 2000)

    ElMessage.success('爬虫任务已启动')
  } catch (error) {
    ElMessage.error('启动爬虫失败')
  }
}

// 检查爬取状态
const checkCrawlStatus = async (taskId) => {
  try {
    const status = await getCrawlStatus(taskId)

    crawlStatus.value.progress = status.progress || 0
    crawlStatus.value.currentStep = status.current_step || ''

    if (status.status === 'success') {
      crawlStatus.value.running = false
      crawlStatus.value.status = 'success'
      clearInterval(crawlTimer)
      ElMessage.success('爬取完成')
      loadCrawlHistory()
    } else if (status.status === 'failed') {
      crawlStatus.value.running = false
      crawlStatus.value.status = 'exception'
      clearInterval(crawlTimer)
      ElMessage.error('爬取失败: ' + status.error_msg)
    }
  } catch (error) {
    console.error('获取状态失败')
  }
}

// 停止爬取
const stopCrawl = async () => {
  try {
    await apiStopCrawl()
    crawlStatus.value.running = false
    if (crawlTimer) {
      clearInterval(crawlTimer)
    }
    ElMessage.info('爬虫已停止')
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

// 加载爬取历史
const loadCrawlHistory = async () => {
  try {
    const data = await getCrawlHistory({ page: 1, page_size: 10 })
    crawlHistory.value = data.data || []
  } catch (error) {
    console.error('加载历史失败')
  }
}

// 文件选择
const handleFileChange = async (file) => {
  try {
    const result = await uploadFile(file.raw)
    fileId.value = result.file_id || ''
    previewData.value = result.preview || []
    columns.value = result.columns || []
    totalRows.value = result.total_rows || 0

    // 自动应用建议的字段映射
    if (result.suggested_mapping) {
      fieldMapping.value = {
        title: result.suggested_mapping.title || '',
        box_office_wan: result.suggested_mapping.box_office_wan || '',
        release_year: result.suggested_mapping.release_year || '',
        avg_price: result.suggested_mapping.avg_price || '',
        per_session_attendance: result.suggested_mapping.per_session_attendance || '',
        ranking: result.suggested_mapping.ranking || '',
        type: result.suggested_mapping.type || '',
        rating: result.suggested_mapping.rating || '',
        rating_count: result.suggested_mapping.rating_count || '',
        wish_count: result.suggested_mapping.wish_count || ''
      }
      ElMessage.success('已自动检测并应用字段映射')
    }

    // 检测需要清理的列
    detectCleanableColumns()
  } catch (error) {
    ElMessage.error('文件解析失败')
  }
}

// 检测需要清理的列
const detectCleanableColumns = () => {
  const cleanTypes = {
    '上映年份': { type: 'year', issue: '格式: "2012-01-11 上映" → 需要提取年份' },
    '年份': { type: 'year', issue: '可能需要提取年份' },
    '累计票房': { type: 'box_office', issue: '格式: "4266.1万"、"1.73亿" → 需要转换为万元数值' },
    '总票房': { type: 'box_office', issue: '格式: "4266.1万"、"1.73亿" → 需要转换为万元数值' },
    '首周票房': { type: 'box_office', issue: '格式: "260.2万" → 需要转换为万元数值' },
    '首日票房': { type: 'box_office', issue: '格式: "1343.8万" → 需要转换为万元数值' },
    '票房预测': { type: 'box_office', issue: '格式: "4471.1万" → 需要转换为万元数值' },
    '分账票房': { type: 'box_office', issue: '格式: "4251.4万" → 需要转换为万元数值' },
    '票房': { type: 'box_office', issue: '格式: "4266.1万"、"1.73亿" → 需要转换为万元数值' },
    '五星占比': { type: 'percentage', issue: '格式: "62.4%" → 需要转换为数值' },
    '四星占比': { type: 'percentage', issue: '格式: "21.8%" → 需要转换为数值' },
    '三星占比': { type: 'percentage', issue: '格式: "9.8%" → 需要转换为数值' },
    '二星占比': { type: 'percentage', issue: '格式: "1.7%" → 需要转换为数值' },
    '一星占比': { type: 'percentage', issue: '格式: "4.3%" → 需要转换为数值' },
    '占比': { type: 'percentage', issue: '格式: "XX%" → 需要转换为数值' },
    '观众评分人数': { type: 'people_count', issue: '格式: "1680观众评分"、"13万观众评分" → 需要提取数字' },
    '评分人数': { type: 'people_count', issue: '格式: "1680"、"13万" → 需要转换为数值' },
    '想看人数': { type: 'people_count', issue: '格式: "9236人想看"、"15.6万人想看" → 需要提取数字' },
    '评价人数': { type: 'people_count', issue: '格式: "13万人评价" → 需要提取数字' },
    '类型': { type: 'type', issue: '格式: "动画,冒险,奇幻" → 取第一个类型' },
    '电影类型': { type: 'type', issue: '格式: "动画,冒险,奇幻" → 取第一个类型' },
    '类型/版本': { type: 'type', issue: '格式: "动画,冒险,奇幻" → 取第一个类型' }
  }

  const cleanable = []
  const status = {}

  for (const col of columns.value) {
    if (cleanTypes[col]) {
      // 获取示例数据
      const sample = previewData.value[0]?.[col] || ''
      cleanable.push({
        column: col,
        clean_type: cleanTypes[col].type,
        sample: String(sample).substring(0, 50),
        issue: cleanTypes[col].issue
      })
      status[col] = 'pending'
    }
  }

  cleanableColumns.value = cleanable
  cleaningStatus.value = status
}

// 清理单列数据
const cleanColumn = async (colInfo) => {
  if (!fileId.value) {
    ElMessage.warning('文件已过期，请重新上传')
    return
  }

  cleaningStatus.value[colInfo.column] = 'cleaning'

  try {
    const result = await cleanData({
      file_id: fileId.value,
      column: colInfo.column,
      clean_type: colInfo.clean_type
    })

    if (result.failed_count > 0 && result.errors.length > 0) {
      ElMessage.warning(`清理完成，但有 ${result.failed_count} 条数据失败`)
    } else {
      ElMessage.success(`成功清理 ${result.success_count} 条数据`)
    }

    // 更新预览数据
    for (let i = 0; i < Math.min(result.original.length, previewData.value.length); i++) {
      if (previewData.value[i][colInfo.column] === result.original[i]) {
        previewData.value[i][colInfo.column] = result.cleaned[i]
      }
    }

    cleaningStatus.value[colInfo.column] = 'completed'

    // 显示清理前后的对比
    ElMessageBox.alert(
      `清理前: ${result.original[0]}<br>清理后: ${result.cleaned[0]}<br><br>` +
      `成功: ${result.success_count} 条，失败: ${result.failed_count} 条`,
      '数据清理结果',
      { dangerouslyUseHTMLString: true, type: 'info' }
    )
  } catch (error) {
    cleaningStatus.value[colInfo.column] = 'failed'
    ElMessage.error(error.response?.data?.detail || '清理失败')
  }
}

// 一键清理全部
const cleanAllColumns = async () => {
  if (cleanableColumns.value.length === 0) {
    ElMessage.info('没有需要清理的列')
    return
  }

  try {
    await ElMessageBox.confirm(
      `即将清理 ${cleanableColumns.value.length} 列数据，是否继续？`,
      '确认清理',
      { type: 'warning' }
    )

    let successCount = 0
    for (const colInfo of cleanableColumns.value) {
      if (cleaningStatus.value[colInfo.column] !== 'completed') {
        await cleanColumn(colInfo)
        if (cleaningStatus.value[colInfo.column] === 'completed') {
          successCount++
        }
      }
    }

    ElMessage.success(`成功清理 ${successCount} 列数据`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量清理失败')
    }
  }
}

// 确认导入
const confirmImport = async () => {
  if (!fieldMapping.value.title || !fieldMapping.value.box_office_wan) {
    ElMessage.warning('请至少映射电影名称和票房字段')
    return
  }

  if (!fileId.value) {
    ElMessage.warning('请先上传文件')
    return
  }

  importing.value = true
  try {
    await importData({
      file_id: fileId.value,
      field_mapping: fieldMapping.value,
      skip_duplicates: true,
      data_source: 'upload'
    })
    ElMessage.success(`成功导入 ${totalRows.value} 条数据`)
    previewData.value = []
    fileId.value = ''
    fieldMapping.value = {
      title: '',
      box_office_wan: '',
      release_year: '',
      avg_price: '',
      per_session_attendance: '',
      ranking: '',
      type: '',
      rating: '',
      rating_count: '',
      wish_count: ''
    }
    activeTab.value = 'list'
    loadMovies()
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error(error.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

// 下载模板
const downloadTemplate = async () => {
  try {
    const blob = await apiDownloadTemplate()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '电影数据模板.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 加载电影列表
const loadMovies = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }

    // 添加搜索参数
    if (searchForm.value.title) {
      params.search = searchForm.value.title
    }

    // 添加类型筛选
    if (searchForm.value.type) {
      params.type = searchForm.value.type
    }

    const data = await getMovies(params)
    movieList.value = data.data || []
    pagination.value.total = data.total || 0
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 重置搜索
const resetSearch = () => {
  searchForm.value = { title: '', type: '' }
  loadMovies()
}

// 查看详情
const viewDetail = (movie) => {
  currentMovie.value = movie
  detailDialog.value = true
}

// 删除电影
const deleteMovie = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这部电影吗？', '提示', {
      type: 'warning'
    })
    await apiDeleteMovie(id)
    ElMessage.success('删除成功')
    loadMovies()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 删除所有电影
const deleteAllMovies = async () => {
  try {
    // 第一次确认
    await ElMessageBox.confirm(
      '此操作将删除所有电影数据，且不可恢复！是否继续？',
      '危险操作',
      {
        type: 'error',
        confirmButtonText: '我了解风险，继续删除',
        cancelButtonText: '取消'
      }
    )

    // 第二次确认
    await ElMessageBox.confirm(
      `即将删除全部 ${pagination.value.total} 部电影数据，请再次确认！`,
      '最后确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )

    await apiDeleteAllMovies()
    ElMessage.success('已清空所有数据')
    pagination.value.total = 0
    movieList.value = []
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 导出数据
const exportData = async () => {
  try {
    const blob = await apiExportData(searchForm.value)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '电影数据.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 状态类型
const getStatusType = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

// 状态文本
const getStatusText = (status) => {
  const map = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败'
  }
  return map[status] || status
}
</script>

<style scoped>
.data-manage {
  padding: 0;
}

.card-tabs {
  margin-bottom: 20px;
}

.tab-content {
  min-height: 500px;
}

.action-buttons {
  margin-top: 20px;
  text-align: center;
}

.progress-wrapper {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.progress-text {
  margin-top: 10px;
  text-align: center;
  color: #606266;
  font-size: 14px;
}

.preview-section {
  margin-top: 30px;
}

.clean-section {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

:deep(.el-upload-dragger) {
  padding: 40px;
}

:deep(.el-radio-button__inner) {
  padding: 12px 20px;
}
</style>
