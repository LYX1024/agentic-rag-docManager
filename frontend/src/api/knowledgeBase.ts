import request, { type ApiResponse } from './request'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  vsType: string
  embedModel: string
  userId: number
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

export function createKB(data: CreateKBParams): Promise<ApiResponse<KnowledgeBase>> {
  return request.post('/kb', data)
}

export function listKBs(page: number = 0, size: number = 20): Promise<ApiResponse<{ records: KnowledgeBase[], total: number }>> {
  return request.get('/kb', { params: { page, size } })
}

export function getKB(id: number): Promise<ApiResponse<KnowledgeBase>> {
  return request.get(`/kb/${id}`)
}

export function updateKB(id: number, data: UpdateKBParams): Promise<ApiResponse<KnowledgeBase>> {
  return request.put(`/kb/${id}`, data)
}

export function deleteKB(id: number): Promise<ApiResponse<null>> {
  return request.delete(`/kb/${id}`)
}

export function getKBStats(id: number): Promise<ApiResponse<Record<string, any>>> {
  return request.get(`/kb/${id}/stats`)
}
