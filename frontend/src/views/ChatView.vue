<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <!-- Session sidebar -->
    <aside class="w-[260px] bg-[#f5f0eb] border-r border-[#d4cdc5] flex flex-col flex-shrink-0">
      <div class="p-4 border-b border-[#d4cdc5] flex flex-col gap-2">
        <AppButton variant="secondary" size="sm" @click="$router.push('/dashboard')">
          ← 返回主页
        </AppButton>
        <AppButton variant="primary" size="sm" @click="showNewSessionDialog">
          新对话
        </AppButton>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="[
            'flex items-center gap-2 px-3 py-2 cursor-pointer font-mono text-sm transition-colors mb-0.5 group',
            session.id === chatStore.currentSessionId
              ? 'bg-[#3d3d3d] text-[#f5f0eb]'
              : 'text-[#3d3d3d] hover:bg-gray-100'
          ]"
          @click="handleSelectSession(session.id)"
        >
          <span></span>
          <span class="flex-1 truncate">{{ session.title }}</span>
          <button
            class="font-mono text-xs opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer w-5 h-5 flex items-center justify-center"
            :class="session.id === chatStore.currentSessionId ? 'text-white hover:text-[#5a7a6b]' : 'text-[#3d3d3d] hover:text-[#5a7a6b]'"
            @click.stop="handleDeleteSession(session.id)"
          >
            ×
          </button>
        </div>
        <div v-if="sessions.length === 0" class="p-10 text-center font-mono text-xs text-gray-400">
          <p>暂无对话记录</p>
          <p class="opacity-70 mt-1">点击上方按钮开始新对话</p>
        </div>
      </div>
    </aside>

    <!-- Main chat area -->
    <div class="flex-1 flex flex-col bg-[#f5f0eb]">
      <!-- Empty state -->
      <div v-if="!chatStore.currentSessionId" class="flex-1 flex flex-col items-center justify-center gap-6">
        <h2 class="font-light tracking-wide text-2xl">智能知识库问答</h2>
        <p class="font-mono text-sm text-gray-500">选择一个知识库，开始智能对话</p>
        <AppButton variant="primary" size="lg" @click="showNewSessionDialog">
          开始新对话
        </AppButton>
      </div>

      <!-- Chat area -->
      <template v-else>
        <!-- Messages -->
        <div ref="scrollContainer" class="flex-1 overflow-y-auto p-4 md:p-6">
          <div v-if="messages.length === 0 && !chatStore.loading" class="flex flex-col items-center justify-center h-full text-gray-400 font-mono text-sm gap-3">
            <span class="text-4xl"></span>
            <p>开始新的对话</p>
          </div>
          <div v-else class="max-w-[800px] mx-auto flex flex-col gap-4">
            <ChatMessageComponent
              v-for="(msg, index) in messages"
              :key="index"
              :message="msg"
            />
            <div v-if="isStreaming" class="flex items-center gap-2 px-4 py-3 bg-[#f5f0eb] border-2 border-[#d4cdc5] self-start">
              <span class="flex gap-1">
                <span class="w-1.5 h-1.5 bg-[#3d3d3d] rounded-none animate-bounce" style="animation-delay: 0ms" />
                <span class="w-1.5 h-1.5 bg-[#3d3d3d] rounded-none animate-bounce" style="animation-delay: 200ms" />
                <span class="w-1.5 h-1.5 bg-[#3d3d3d] rounded-none animate-bounce" style="animation-delay: 400ms" />
              </span>
              <span class="font-mono text-xs text-gray-500">AI 正在思考...</span>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="p-4 bg-[#f5f0eb] border-t-2 border-[#d4cdc5]">
          <div class="max-w-[800px] mx-auto">
            <textarea
              v-model="inputText"
              :placeholder="inputPlaceholder"
              rows="2"
              class="bg-transparent focus:outline-none border-2 border-[#d4cdc5] px-3 py-2 w-full font-mono text-sm resize-none placeholder:text-gray-400"
              @keyup.enter.exact="handleSend"
            />
            <div class="flex items-center justify-between mt-2">
              <span class="font-mono text-xs text-gray-400">Enter 发送，Shift+Enter 换行</span>
              <AppButton
                variant="primary"
                size="sm"
                :disabled="!inputText.trim() || isStreaming"
                @click="handleSend"
              >
                {{ isStreaming ? '生成中...' : '发送' }}
              </AppButton>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- New session dialog -->
    <AppDialog
      :model-value="showKBDialog"
      title="选择知识库"
      width="480px"
      @update:model-value="showKBDialog = $event"
    >
      <AppSelect
        v-model="selectedKBId"
        :options="kbOptions"
        placeholder="请选择知识库"
      />
      <template #footer>
        <AppButton variant="secondary" @click="showKBDialog = false">取消</AppButton>
        <AppButton variant="primary" :disabled="!selectedKBId" @click="handleCreateSession">
          开始对话
        </AppButton>
      </template>
    </AppDialog>

    <!-- Delete confirm dialog -->
    <AppDialog
      :model-value="showDeleteDialog"
      title="确认删除"
      width="400px"
      @update:model-value="showDeleteDialog = $event"
    >
      <p class="font-mono text-sm">确定要删除该对话吗？</p>
      <template #footer>
        <AppButton variant="secondary" @click="showDeleteDialog = false">取消</AppButton>
        <AppButton variant="danger" @click="confirmDeleteSession">确定删除</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useKBStore } from '@/stores/knowledgeBase'
import type { KnowledgeBase } from '@/api/knowledgeBase'
import type { ChatMessage, ChatSource } from '@/api/chat'
import { ragChatSSE, deleteSession } from '@/api/chat'
import { Toast } from '@/utils/toast'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import ChatMessageComponent from '@/components/chat/ChatMessage.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const kbStore = useKBStore()

const inputText = ref('')
const isStreaming = ref(false)
const showKBDialog = ref(false)
const selectedKBId = ref<number | null>(null)
const activeKBId = ref<number | null>(null)
const kbList = ref<KnowledgeBase[]>([])
const showDeleteDialog = ref(false)
const deleteTargetId = ref<number | null>(null)
const scrollContainer = ref<HTMLElement | null>(null)

let activeEventSource: EventSource | null = null

const inputPlaceholder = computed(() => {
  return isStreaming.value ? 'AI 正在生成回答...' : '输入您的问题...'
})

const sessions = computed(() => chatStore.sessions)
const messages = computed(() => chatStore.messages)

const kbOptions = computed(() =>
  kbList.value.map(kb => ({ label: kb.name, value: kb.id }))
)

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

// Watch for message changes to auto-scroll
watch(
  () => messages.value.length,
  () => scrollToBottom()
)

watch(
  () => messages.value[messages.value.length - 1]?.content,
  () => scrollToBottom()
)

onMounted(async () => {
  await chatStore.fetchSessions()
  await kbStore.fetchKBList()
  kbList.value = kbStore.kbList

  const sessionId = route.params.sessionId
  if (sessionId) {
    await chatStore.selectSession(Number(sessionId))
    const session = chatStore.sessions.find(s => s.id === Number(sessionId))
    activeKBId.value = session?.kbId ?? null
  }
})

onUnmounted(() => {
  closeSSE()
})

function closeSSE() {
  if (activeEventSource) {
    activeEventSource.close()
    activeEventSource = null
  }
  isStreaming.value = false
}

function showNewSessionDialog() {
  selectedKBId.value = null
  showKBDialog.value = true
}

async function handleCreateSession() {
  if (!selectedKBId.value) return

  const kb = kbList.value.find(k => k.id === selectedKBId.value)
  const title = kb ? `与 ${kb.name} 的对话` : '新对话'

  try {
    await chatStore.createSession(selectedKBId.value, title)
    activeKBId.value = selectedKBId.value
    showKBDialog.value = false
    Toast.success('对话已创建')
    router.replace(`/chat/${chatStore.currentSessionId}`)
  } catch {
    Toast.error('创建对话失败')
  }
}

async function handleSelectSession(id: number) {
  if (id === chatStore.currentSessionId) return
  closeSSE()
  const session = chatStore.sessions.find(s => s.id === id)
  activeKBId.value = session?.kbId ?? null
  await chatStore.selectSession(id)
  router.replace(`/chat/${id}`)
}

function handleDeleteSession(id: number) {
  deleteTargetId.value = id
  showDeleteDialog.value = true
}

async function confirmDeleteSession() {
  if (!deleteTargetId.value) return
  try {
    await deleteSession(deleteTargetId.value)
    chatStore.sessions = chatStore.sessions.filter(s => s.id !== deleteTargetId.value)
    if (chatStore.currentSessionId === deleteTargetId.value) {
      chatStore.clearMessages()
      activeKBId.value = null
    }
    showDeleteDialog.value = false
    Toast.success('对话已删除')
  } catch {
    Toast.error('删除失败')
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  const kbId = activeKBId.value
  if (!kbId) {
    Toast.warning('请先选择知识库')
    return
  }

  // Add user message
  const userMsg: ChatMessage = {
    role: 'user',
    content: text
  }
  chatStore.addMessage(userMsg)
  inputText.value = ''

  // Add placeholder AI message
  const aiMsg: ChatMessage = {
    role: 'assistant',
    content: ''
  }
  chatStore.addMessage(aiMsg)

  isStreaming.value = true

  const sessionId = chatStore.currentSessionId ?? undefined

  activeEventSource = ragChatSSE(
    {
      query: text,
      kbId,
      sessionId
    },
    {
      onToken: (token: string) => {
        chatStore.updateLastMessage(token)
      },
      onSources: (sources: ChatSource[]) => {
        chatStore.setLastMessageSources(sources)
      },
      onError: (error: string) => {
        Toast.error(error)
        closeSSE()
      },
      onComplete: () => {
        closeSSE()
      }
    }
  )
}
</script>
