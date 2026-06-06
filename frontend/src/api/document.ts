import request, { type ApiResponse } from './request'

export interface Document {
  id: number
  kbId: number
  category: string
  fileName: string
  fileExt: string
  fileSize: number
  filePathInMinio: string
  fileVersion: number
  status: DocumentStatus
  errorMsg: string | null
  chunkCount: number
  createdAt: string
  updatedAt: string
}

export type DocumentStatus = 'UPLOADED' | 'PARSING' | 'CHUNKING' | 'EMBEDDING' | 'COMPLETED' | 'FAILED'

export function uploadFile(kbId: number, file: File, category?: string): Promise<ApiResponse<Document>> {
  const formData = new FormData()
  formData.append('file', file)
  let url = `/doc/upload?kbId=${kbId}`
  if (category) {
    url += `&category=${encodeURIComponent(category)}`
  }
  return request.post(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function listDocs(kbId: number, category?: string, page: number = 0, size: number = 20): Promise<ApiResponse<{ records: Document[], total: number }>> {
  const params: Record<string, any> = { kbId, page, size }
  if (category) params.category = category
  return request.get('/doc/list', { params })
}

export function getCategories(kbId: number): Promise<ApiResponse<string[]>> {
  return request.get('/doc/categories', { params: { kbId } })
}

export function getDocStatus(id: number): Promise<ApiResponse<string>> {
  return request.get(`/doc/${id}/status`)
}

export function deleteDoc(id: number): Promise<ApiResponse<null>> {
  return request.delete(`/doc/${id}`)
}
