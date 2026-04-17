import request from './index'

// 单个预测
export function predictSingle(params) {
  return request({
    url: '/predict/single',
    method: 'post',
    params
  })
}

// 批量预测
export function predictBatch(file, modelType) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/predict/batch',
    method: 'post',
    data: formData,
    params: { model_type: modelType },
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取预测历史
export function getPredictionHistory(params) {
  return request({
    url: '/predict/history',
    method: 'get',
    params
  })
}

// 获取预测详情
export function getPredictionDetail(id) {
  return request({
    url: `/predict/${id}`,
    method: 'get'
  })
}

// 对比预测
export function comparePredictions(movieId) {
  return request({
    url: `/predict/compare/${movieId}`,
    method: 'get'
  })
}
