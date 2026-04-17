import request from './index'

// 开始训练
export function startTrain(params) {
  return request({
    url: '/model/train',
    method: 'post',
    params
  })
}

// 获取训练状态
export function getTrainStatus(taskId) {
  return request({
    url: '/model/status',
    method: 'get',
    params: { task_id: taskId }
  })
}

// 获取模型列表
export function getModelList(modelType) {
  return request({
    url: '/model/list',
    method: 'get',
    params: { model_type: modelType }
  })
}

// 选择模型
export function selectModel(modelId) {
  return request({
    url: '/model/select',
    method: 'post',
    params: { model_id: modelId }
  })
}

// 获取模型指标
export function getModelMetrics(modelType) {
  return request({
    url: `/model/metrics/${modelType}`,
    method: 'get'
  })
}
