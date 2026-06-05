import request, { type ApiResponse } from './request'

export interface ChatSession {
  id: number
  userId: number
  kbId: number
  title: string
  createdAt?: string
  updatedAt?: string
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  createdAt?: string
}

export interface ChatSource {
  file_name: string
  chunk_index: number
  score: number
  text: string
}

export function createSession(userId: number, kbId: number, title: string): Promise<ApiResponse<ChatSession>> {
  return request.post('/chat/session/create', { userId, kbId, title }).then(res => res.data)
}

export function listSessions(): Promise<ApiResponse<ChatSession[]>> {
  return request.get('/chat/sessions').then(res => res.data)
}

export function getHistory(sessionId: number): Promise<ApiResponse<ChatMessage[]>> {
  return request.get(`/chat/session/${sessionId}/history`).then(res => res.data)
}

export function deleteSession(sessionId: number): Promise<ApiResponse<null>> {
  return request.delete(`/chat/session/${sessionId}`).then(res => res.data)
}

export interface SSEParams {
  query: string
  kbId: number
  sessionId?: number
}

export interface SSECallbacks {
  onToken: (token: string) => void
  onSources: (sources: ChatSource[]) => void
  onError: (error: string) => void
  onComplete: () => void
}

/**
 * Create SSE connection for RAG chat streaming.
 * Returns EventSource instance for cleanup by the caller.
 */
export function ragChatSSE(params: SSEParams, callbacks: SSECallbacks): EventSource {
  const token = localStorage.getItem('sa-token') || ''
  const sessionParam = params.sessionId ? `&sessionId=${params.sessionId}` : ''

  const url = `/api/chat/rag?query=${encodeURIComponent(params.query)}&kbId=${params.kbId}${sessionParam}&sa-token=${encodeURIComponent(token)}`
  const eventSource = new EventSource(url)

  let fullContent = ''

  eventSource.addEventListener('token', (event: MessageEvent) => {
    const data = event.data
    if (data) {
      fullContent += data
      callbacks.onToken(data)
    }
  })

  eventSource.addEventListener('sources', (event: MessageEvent) => {
    try {
      const sources = JSON.parse(event.data) as ChatSource[]
      callbacks.onSources(sources)
    } catch {
      // ignore parse errors
    }
  })

  eventSource.addEventListener('error', () => {
    if (eventSource.readyState === EventSource.CLOSED) {
      // Clean close after stream ends
      callbacks.onComplete()
      return
    }
    callbacks.onError('连接中断，请重试')
  })

  eventSource.addEventListener('done', () => {
    eventSource.close()
    callbacks.onComplete()
  })

  return eventSource
}
