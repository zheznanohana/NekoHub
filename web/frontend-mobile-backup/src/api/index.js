import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器 - 添加 Token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  // 认证
  login: (credentials) => api.post('/auth/login', credentials),
  changePassword: (newPassword) => api.post('/auth/change-password', { new_password: newPassword }),
  
  // 消息
  getMessages: (limit) => api.get(`/messages?limit=${limit}`),
  markRead: (id) => api.post(`/messages/${id}/read`),
  
  // 任务
  getTasks: () => api.get('/tasks'),
  createTask: (task) => api.post('/tasks', task),
  deleteTask: (id) => api.delete(`/tasks/${id}`),
  runTask: (id) => api.post(`/tasks/${id}/run`),
  
  // AI
  chat: (message, domains, limit) => api.post('/ai/chat', { message, domains, limit }),
  
  // 设置
  getSettings: () => api.get('/settings'),
  updateSettings: (settings) => api.post('/settings', settings),
  
  // 测试
  testGotify: (config) => api.post('/gotify/test', config),
  testForward: (config) => api.post('/forward/test', config)
}
