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

export interface LoginResult {
  token: string
  user: UserInfo
}

export function login(params: LoginParams): Promise<ApiResponse<LoginResult>> {
  return request.post('/auth/login', params).then(res => res.data)
}

export function register(params: RegisterParams): Promise<ApiResponse<null>> {
  return request.post('/auth/register', params).then(res => res.data)
}

export function getMe(): Promise<ApiResponse<UserInfo>> {
  return request.get('/auth/me').then(res => res.data)
}

export function logout(): Promise<ApiResponse<null>> {
  return request.post('/auth/logout').then(res => res.data)
}
