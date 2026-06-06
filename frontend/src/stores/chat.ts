import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '@/api/chat'
import { useAuthStore } from '@/stores/auth'
import type { ChatSession, ChatMessage as ChatMessageType } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const authStore = useAuthStore()
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref<number | null>(null)
  const messages = ref<ChatMessageType[]>([])
  const loading = ref(false)

  async function fetchSessions() {
    const res = await chatApi.listSessions()
    sessions.value = res.data
  }

  async function createSession(kbId: number, title: string) {
    const res = await chatApi.createSession(kbId, title)
    sessions.value.unshift(res.data)
    currentSessionId.value = res.data.id
    messages.value = []
    return res.data
  }

  async function selectSession(sessionId: number) {
    currentSessionId.value = sessionId
    loading.value = true
    try {
      const res = await chatApi.getHistory(sessionId)
      messages.value = (res.data || []).map(m => ({
        ...m,
        sources: typeof m.sources === 'string' ? JSON.parse(m.sources || '[]') : (m.sources || [])
      }))
    } finally {
      loading.value = false
    }
  }

  function addMessage(message: ChatMessageType) {
    messages.value.push(message)
  }

  function updateLastMessage(content: string) {
    if (messages.value.length > 0) {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg.role === 'assistant') {
        lastMsg.content += content
      }
    }
  }

  function setLastMessageSources(sources: chatApi.ChatSource[]) {
    if (messages.value.length > 0) {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg.role === 'assistant') {
        lastMsg.sources = sources
      }
    }
  }

  function clearMessages() {
    messages.value = []
    currentSessionId.value = null
  }

  return {
    sessions,
    currentSessionId,
    messages,
    loading,
    fetchSessions,
    createSession,
    selectSession,
    addMessage,
    updateLastMessage,
    setLastMessageSources,
    clearMessages
  }
})
