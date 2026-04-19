import request from './index'

export function startTrain(params) {
  return request({
    url: '/model/train',
    method: 'post',
    params
  })
}

export function getTrainStatus(taskId) {
  return request({
    url: '/model/status',
    method: 'get',
    params: { task_id: taskId }
  })
}

export function getModelList(modelType) {
  return request({
    url: '/model/list',
    method: 'get',
    params: { model_type: modelType }
  })
}

export function selectModel(modelType) {
  return request({
    url: '/model/select',
    method: 'post',
    params: { model_type: modelType }
  })
}

export function getModelMetrics(modelType) {
  return request({
    url: `/model/metrics/${modelType}`,
    method: 'get'
  })
}
