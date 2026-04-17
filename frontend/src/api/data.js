import request from './index'

// 获取电影列表
export function getMovies(params) {
  return request({
    url: '/data/movies',
    method: 'get',
    params
  })
}

// 获取电影详情
export function getMovieDetail(id) {
  return request({
    url: `/data/movies/${id}`,
    method: 'get'
  })
}

// 删除电影
export function deleteMovie(id) {
  return request({
    url: `/data/movies/${id}`,
    method: 'delete'
  })
}

// 上传文件
export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/data/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 导入数据
export function importData(data) {
  return request({
    url: '/data/import',
    method: 'post',
    data
  })
}

// 获取数据统计
export function getDataStats() {
  return request({
    url: '/data/stats',
    method: 'get'
  })
}

// 下载模板
export function downloadTemplate() {
  return request({
    url: '/data/template',
    method: 'get',
    responseType: 'blob'
  })
}

// 导出数据
export function exportData(params) {
  return request({
    url: '/data/export',
    method: 'post',
    data: params,
    responseType: 'blob'
  })
}

// 删除所有电影
export function deleteAllMovies() {
  return request({
    url: '/data/movies/all',
    method: 'delete',
    params: { confirm: true }
  })
}

// 清理数据
export function cleanData(data) {
  return request({
    url: '/data/clean',
    method: 'post',
    data
  })
}
