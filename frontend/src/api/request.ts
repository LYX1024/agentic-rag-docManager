import axios, { type AxiosInstance, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { Toast } from '@/utils/toast'
import router from '@/router'

export interface ApiResponse<T = any> {
  code: number
  msg: string
  data: T
}

const service: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('sa-token')
    if (token) {
      config.headers['sa-token'] = token
    }
    return config
  },
  (error: any) => {
    return Promise.reject(error)
  }
)

// Response interceptor
service.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>): any => {
    const res = response.data

    // If response is a blob or other non-JSON, return directly
    if (response.config.responseType === 'blob') {
      return response
    }

    if (res.code === 200 || res.code === 0) {
      return res
    } else {
      Toast.error(res.msg || '请求失败')

      if (res.code === 401) {
        localStorage.removeItem('sa-token')
        router.push('/login')
      }

      return Promise.reject(new Error(res.msg || 'Error'))
    }
  },
  (error: any) => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        localStorage.removeItem('sa-token')
        router.push('/login')
        Toast.error('登录已过期，请重新登录')
      } else {
        Toast.error(error.response.data?.msg || `请求失败 (${status})`)
      }
    } else if (error.message.includes('timeout')) {
      Toast.error('请求超时，请稍后重试')
    } else {
      Toast.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default service
