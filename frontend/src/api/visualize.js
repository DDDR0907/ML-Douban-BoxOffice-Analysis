import request from './index'

export function getRatingBoxOfficeData() {
  return request({
    url: '/visualize/rating-boxoffice',
    method: 'get'
  })
}

export function getGenreDistribution() {
  return request({
    url: '/visualize/genre-distribution',
    method: 'get'
  })
}

export function getModelComparison() {
  return request({
    url: '/visualize/model-comparison',
    method: 'get'
  })
}

export function getFeatureImportance(modelType) {
  return request({
    url: '/visualize/feature-importance',
    method: 'get',
    params: { model_type: modelType }
  })
}

export function getFeatureCorrelationHeatmap(limit = 12) {
  return request({
    url: '/visualize/feature-correlation-heatmap',
    method: 'get',
    params: { limit }
  })
}

export function getMultiModelFeatureImportance(limit = 10) {
  return request({
    url: '/visualize/multi-model-feature-importance',
    method: 'get',
    params: { limit }
  })
}

export function getPredictComparison(params) {
  return request({
    url: '/visualize/predict-comparison',
    method: 'get',
    params
  })
}

export function getYearTrend() {
  return request({
    url: '/visualize/year-trend',
    method: 'get'
  })
}

export function getTopMovies(by, limit) {
  return request({
    url: '/visualize/top-movies',
    method: 'get',
    params: { by, limit }
  })
}

export function getDataOverview() {
  return request({
    url: '/visualize/data-overview',
    method: 'get'
  })
}
