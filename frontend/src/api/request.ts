import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default api

// 模型配置 API
export const modelApi = {
  getAll: () => api.get('/models/'),
  getOne: (id: number) => api.get(`/models/${id}`),
  create: (data: any) => api.post('/models/', data),
  update: (id: number, data: any) => api.put(`/models/${id}`, data),
  delete: (id: number) => api.delete(`/models/${id}`),
  setDefault: (id: number) => api.put(`/models/${id}/default`),
}

// 搜索 API
export const searchApi = {
  getRecords: (limit = 50) => api.get(`/search/records?limit=${limit}`),
  deleteRecord: (id: number) => api.delete(`/search/records/${id}`),
}

// 提示词 API
export const promptApi = {
  getRecords: (limit = 50) => api.get(`/prompt/records?limit=${limit}`),
  deleteRecord: (id: number) => api.delete(`/prompt/records/${id}`),
}

// 问答 API
export const quizApi = {
  getCategories: () => api.get('/quiz/categories'),
  getHistory: (limit = 50) => api.get(`/quiz/history?limit=${limit}`),
  getSession: (id: number) => api.get(`/quiz/session/${id}`),
}

// 知识库 API
export const knowledgeApi = {
  getAll: (params?: any) => api.get('/knowledge/', { params }),
  create: (data: any) => api.post('/knowledge/', data),
  delete: (id: number) => api.delete(`/knowledge/${id}`),
  getStats: () => api.get('/knowledge/stats'),
}
