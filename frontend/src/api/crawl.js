import request from './index'

// 开始爬取
export function startCrawl(params) {
  return request({
    url: '/crawl/start',
    method: 'post',
    params
  })
}

// 停止爬取
export function stopCrawl() {
  return request({
    url: '/crawl/stop',
    method: 'post'
  })
}

// 获取爬取状态
export function getCrawlStatus(taskId) {
  return request({
    url: '/crawl/status',
    method: 'get',
    params: { task_id: taskId }
  })
}

// 获取爬虫配置
export function getCrawlConfig() {
  return request({
    url: '/crawl/config',
    method: 'get'
  })
}

// 更新爬虫配置
export function updateCrawlConfig(data) {
  return request({
    url: '/crawl/config',
    method: 'put',
    data
  })
}

// 获取爬取历史
export function getCrawlHistory(params) {
  return request({
    url: '/crawl/history',
    method: 'get',
    params
  })
}
