import request, { type ApiResponse } from './request'

export interface SearchParams {
  query: string
  kbId: number
  topK?: number
  scoreThreshold?: number
  searchMode?: 'hybrid' | 'vector' | 'bm25'
  alpha?: number // BM25 weight for hybrid search (0-1)
  beta?: number  // Vector weight for hybrid search (0-1)
}

export interface HybridSearchParams {
  query: string
  kbId: number
  topK?: number
  scoreThreshold?: number
  alpha?: number
  beta?: number
}

export interface SearchResultItem {
  id: string
  text: string
  score: number
  fileSource: string
  chunkIndex: number
  metadata?: Record<string, any>
}

export interface SearchResult {
  results: SearchResultItem[]
  total: number
  query: string
  searchMode: string
  timeCost?: number
}

export function search(data: SearchParams): Promise<ApiResponse<SearchResult>> {
  return request.post('/search', data).then(res => res.data)
}

export function hybridSearch(data: HybridSearchParams): Promise<ApiResponse<SearchResult>> {
  return request.post('/search/hybrid', data).then(res => res.data)
}
