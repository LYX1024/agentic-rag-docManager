import request, { type ApiResponse } from './request'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  vsType: string
  embedModel: string
  fileCount?: number
  createdAt?: string
  updatedAt?: string
}

export interface CreateKBParams {
  name: string
  description?: string
  vsType: string
  embedModel: string
}

export interface UpdateKBParams {
  name?: string
  description?: string
  vsType?: string
  embedModel?: string
}

export interface PaginatedResult<T> {
  records: T[]
  total: number
  size: number
  current: number
}

export function createKB(data: CreateKBParams): Promise<ApiResponse<KnowledgeBase>> {
  return request.post('/knowledge-base/create', data).then(res => res.data)
}

export function listKBs(page: number = 1, size: number = 20): Promise<ApiResponse<PaginatedResult<KnowledgeBase>>> {
  return request.get('/knowledge-base/list', { params: { page, size } }).then(res => res.data)
}

export function getKB(id: number): Promise<ApiResponse<KnowledgeBase>> {
  return request.get(`/knowledge-base/${id}`).then(res => res.data)
}

export function updateKB(id: number, data: UpdateKBParams): Promise<ApiResponse<KnowledgeBase>> {
  return request.put(`/knowledge-base/${id}`, data).then(res => res.data)
}

export function deleteKB(id: number): Promise<ApiResponse<null>> {
  return request.delete(`/knowledge-base/${id}`).then(res => res.data)
}

export interface KBStats {
  totalDocs: number
  totalChunks: number
  vsType: string
  embedModel: string
  storageSize: number
}

export function getKBStats(id: number): Promise<ApiResponse<KBStats>> {
  return request.get(`/knowledge-base/${id}/stats`).then(res => res.data)
}
