import request, { type ApiResponse } from './request'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
  email: string
}

export interface UserInfo {
  id: number
  username: string
  email: string
  avatar?: string
  createdAt?: string
}

export function login(params: LoginParams): Promise<ApiResponse<string>> {
  return request.post('/auth/login', params)
}

export function register(params: RegisterParams): Promise<ApiResponse<null>> {
  return request.post('/auth/register', params)
}

export function getMe(): Promise<ApiResponse<UserInfo>> {
  return request.get('/auth/me')
}

export function logout(): Promise<ApiResponse<null>> {
  return request.post('/auth/logout')
}
