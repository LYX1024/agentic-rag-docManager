import request, { type ApiResponse } from './request'

export interface ChatSession {
  id: number
  userId: number
  kbId: number
  title: string
  createdAt?: string
  updatedAt?: string
}

export interface ChatSource {
  file_name: string
  chunk_index: number
  chunk_text?: string
  text?: string
  score: number
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: string | any[]
  createdAt?: string
}

export function createSession(kbId: number, title: string): Promise<ApiResponse<ChatSession>> {
  return request.post('/chat/session', { kbId, title })
}

export function listSessions(): Promise<ApiResponse<ChatSession[]>> {
  return request.get('/chat/sessions')
}

export function getHistory(sessionId: number): Promise<ApiResponse<ChatMessage[]>> {
  return request.get(`/chat/session/${sessionId}/history`)
}

export function deleteSession(sessionId: number): Promise<ApiResponse<null>> {
  return request.delete(`/chat/session/${sessionId}`)
}

export interface SSEParams {
  query: string
  kbId: number
  sessionId?: number
}

export interface SSECallbacks {
  onToken: (token: string) => void
  onSources: (sources: any) => void
  onError: (error: string) => void
  onComplete: () => void
}

export function ragChatSSE(params: SSEParams, callbacks: SSECallbacks): EventSource {
  const token = localStorage.getItem('sa-token') || ''
  const sessionParam = params.sessionId ? `&sessionId=${params.sessionId}` : ''

  const url = `/api/chat/rag?query=${encodeURIComponent(params.query)}&kbId=${params.kbId}${sessionParam}&sa-token=${encodeURIComponent(token)}`
  const eventSource = new EventSource(url)

  eventSource.addEventListener('token', (event: MessageEvent) => {
    if (event.data) {
      callbacks.onToken(event.data)
    }
  })

  eventSource.addEventListener('sources', (event: MessageEvent) => {
    try {
      const sources = JSON.parse(event.data)
      callbacks.onSources(sources)
    } catch {
      callbacks.onSources(event.data)
    }
  })

  eventSource.addEventListener('error', (event: MessageEvent) => {
    eventSource.close()
    if (eventSource.readyState === EventSource.CLOSED) {
      callbacks.onComplete()
    } else {
      callbacks.onError('连接中断，请重试')
    }
  })

  return eventSource
}
