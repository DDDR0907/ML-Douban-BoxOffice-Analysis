import request from './index'

// 评分-票房散点图
export function getRatingBoxOfficeData() {
  return request({
    url: '/visualize/rating-boxoffice',
    method: 'get'
  })
}

// 类型票房分布
export function getGenreDistribution() {
  return request({
    url: '/visualize/genre-distribution',
    method: 'get'
  })
}

// 模型性能对比
export function getModelComparison() {
  return request({
    url: '/visualize/model-comparison',
    method: 'get'
  })
}

// 特征重要性
export function getFeatureImportance(modelType) {
  return request({
    url: '/visualize/feature-importance',
    method: 'get',
    params: { model_type: modelType }
  })
}

// 预测vs实际对比
export function getPredictComparison(params) {
  return request({
    url: '/visualize/predict-comparison',
    method: 'get',
    params
  })
}

// 年度趋势
export function getYearTrend() {
  return request({
    url: '/visualize/year-trend',
    method: 'get'
  })
}

// Top电影
export function getTopMovies(by, limit) {
  return request({
    url: '/visualize/top-movies',
    method: 'get',
    params: { by, limit }
  })
}

// 数据概览
export function getDataOverview() {
  return request({
    url: '/visualize/data-overview',
    method: 'get'
  })
}
