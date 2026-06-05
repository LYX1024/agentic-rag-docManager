import request, { type ApiResponse } from './request'

export interface Document {
  id: number
  filename: string
  fileSize: number
  fileType: string
  status: DocumentStatus
  kbId: number
  chunkCount?: number
  createdAt?: string
  updatedAt?: string
}

export type DocumentStatus = 'UPLOADED' | 'PARSING' | 'CHUNKING' | 'EMBEDDING' | 'COMPLETED' | 'FAILED'

export interface PaginatedResult<T> {
  records: T[]
  total: number
  size: number
  current: number
}

export function uploadFile(kbId: number, file: File): Promise<ApiResponse<Document>> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/knowledge-base/${kbId}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data)
}

export function listDocs(kbId: number, page: number = 1, size: number = 20): Promise<ApiResponse<PaginatedResult<Document>>> {
  return request.get(`/knowledge-base/${kbId}/documents`, { params: { page, size } }).then(res => res.data)
}

export function getDocStatus(id: number): Promise<ApiResponse<Document>> {
  return request.get(`/documents/${id}/status`).then(res => res.data)
}

export function deleteDoc(id: number, kbId: number): Promise<ApiResponse<null>> {
  return request.delete(`/knowledge-base/${kbId}/documents/${id}`).then(res => res.data)
}

export function searchDocs(kbId: number, keyword: string): Promise<ApiResponse<Document[]>> {
  return request.get(`/knowledge-base/${kbId}/documents/search`, { params: { keyword } }).then(res => res.data)
}
