import axios from 'axios'
import type { AxiosResponse } from 'axios'

// 响应拦截器已将 AxiosResponse 转为 response.data，使用 any 避免组件重复解包。
const api: any = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: any) => {
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
  testConnection: (id: number) => api.post(`/models/${id}/test`),
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
  getTemplates: (params?: { limit?: number; q?: string }) => api.get('/prompt/templates', { params }),
  getTemplate: (id: number) => api.get(`/prompt/templates/${id}`),
  createTemplate: (data: any) => api.post('/prompt/templates', data),
  updateTemplate: (id: number, data: any) => api.put(`/prompt/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete(`/prompt/templates/${id}`),
  getVersions: (templateId: number) => api.get(`/prompt/templates/${templateId}/versions`),
  createVersion: (templateId: number, data: any) => api.post(`/prompt/templates/${templateId}/versions`, data),
  compareVersions: (templateId: number, fromVersion: number, toVersion: number) => api.get(
    `/prompt/templates/${templateId}/diff`,
    { params: { from_version: fromVersion, to_version: toVersion } },
  ),
  render: (data: any) => api.post('/prompt/render', data),
  test: (data: any) => api.post('/prompt/test', data),
}

// 问答 API
export const quizApi = {
  getCategories: () => api.get('/quiz/categories'),
  getHistory: (limit = 50) => api.get(`/quiz/history?limit=${limit}`),
  getSession: (id: number) => api.get(`/quiz/session/${id}`),
  getWrongAnswers: (params?: { limit?: number; category?: string; knowledge_id?: number }) =>
    api.get('/quiz/wrong-answers', { params }),
  getWeaknessStats: () => api.get('/quiz/weaknesses'),
}

// 知识库 API
export const knowledgeApi = {
  getAll: (params?: any) => api.get('/knowledge/', { params }),
  create: (data: any) => api.post('/knowledge/', data),
  delete: (id: number) => api.delete(`/knowledge/${id}`),
  getStats: () => api.get('/knowledge/stats'),
  search: (query: string, limit = 10) => api.get('/knowledge/search', { params: { q: query, limit } }),
  importUrl: (data: any) => api.post('/knowledge/import-url', data),
  startCrawl: (data: any) => api.post('/knowledge/crawl', data),
  getImportTask: (id: number) => api.get(`/knowledge/crawl/tasks/${id}`),
  getImportTasks: (limit = 20) => api.get('/knowledge/crawl/tasks', { params: { limit } }),
}
