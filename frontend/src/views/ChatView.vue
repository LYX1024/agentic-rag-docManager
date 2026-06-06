<template>
  <div class="chat-page">
    <!-- Session sidebar -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button :icon="ArrowLeft" size="default" @click="$router.push('/dashboard')">
          返回主页
        </el-button>
        <el-button
          type="primary"
          :icon="Plus"
          size="default"
          class="new-session-btn"
          @click="showNewSessionDialog"
        >
          新对话
        </el-button>
      </div>
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="['session-item', { active: session.id === chatStore.currentSessionId }]"
          @click="handleSelectSession(session.id)"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-title">{{ session.title }}</span>
          <el-button
            class="delete-btn"
            :icon="Delete"
            text
            size="small"
            @click.stop="handleDeleteSession(session.id)"
          />
        </div>
        <div v-if="sessions.length === 0" class="no-sessions">
          <p>暂无对话记录</p>
          <p class="hint">点击上方按钮开始新对话</p>
        </div>
      </div>
    </div>

    <!-- Main chat area -->
    <div class="chat-main">
      <div v-if="!chatStore.currentSessionId" class="chat-empty-state">
        <div class="brand-area">
          <el-icon :size="64" color="#409eff"><Cpu /></el-icon>
          <h2>智能知识库问答</h2>
          <p>选择一个知识库，开始智能对话</p>
        </div>
        <el-button type="primary" size="large" @click="showNewSessionDialog">
          开始新对话
        </el-button>
      </div>

      <template v-else>
        <ChatWindow
          :messages="chatStore.messages"
          :loading="chatStore.loading"
          :is-streaming="isStreaming"
        />

        <div class="chat-input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            :placeholder="inputPlaceholder"
            resize="none"
            @keyup.enter.exact="handleSend"
          />
          <div class="input-actions">
            <span class="input-hint">Enter 发送，Shift+Enter 换行</span>
            <el-button
              type="primary"
              :icon="Promotion"
              :disabled="!inputText.trim() || isStreaming"
              :loading="isStreaming"
              @click="handleSend"
            >
              发送
            </el-button>
          </div>
        </div>
      </template>
    </div>

    <!-- New session dialog -->
    <el-dialog
      v-model="showKBDialog"
      title="选择知识库"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-select v-model="selectedKBId" placeholder="请选择知识库" style="width: 100%" filterable>
        <el-option
          v-for="kb in kbList"
          :key="kb.id"
          :label="kb.name"
          :value="kb.id"
        >
          <div class="kb-option">
            <span>{{ kb.name }}</span>
            <el-tag size="small" type="info">{{ kb.fileCount ?? 0 }} 个文件</el-tag>
          </div>
        </el-option>
      </el-select>
      <template #footer>
        <el-button @click="showKBDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedKBId" @click="handleCreateSession">
          开始对话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Promotion, ChatDotRound, Cpu, ArrowLeft } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useKBStore } from '@/stores/knowledgeBase'
import type { KnowledgeBase } from '@/api/knowledgeBase'
import { ragChatSSE, deleteSession } from '@/api/chat'
import type { ChatMessage, ChatSource } from '@/api/chat'
import ChatWindow from '@/components/chat/ChatWindow.vue'

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

let activeEventSource: EventSource | null = null

const inputPlaceholder = computed(() => {
  return isStreaming.value ? 'AI 正在生成回答...' : '输入您的问题...'
})

const sessions = computed(() => chatStore.sessions)

onMounted(async () => {
  await chatStore.fetchSessions()
  await kbStore.fetchKBList()
  kbList.value = kbStore.kbList

  // If there's a sessionId in the route, select it
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
    ElMessage.success('对话已创建')
    router.replace(`/chat/${chatStore.currentSessionId}`)
  } catch {
    ElMessage.error('创建对话失败')
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

async function handleDeleteSession(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除该对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteSession(id)
    chatStore.sessions = chatStore.sessions.filter(s => s.id !== id)
    if (chatStore.currentSessionId === id) {
      chatStore.clearMessages()
      activeKBId.value = null
    }
    ElMessage.success('对话已删除')
  } catch {
    // cancelled
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return

  const kbId = activeKBId.value
  if (!kbId) {
    ElMessage.warning('请先选择知识库')
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
        ElMessage.error(error)
        closeSSE()
      },
      onComplete: () => {
        closeSSE()
      }
    }
  )
}
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;

  .chat-sidebar {
    width: 260px;
    background: #001529;
    display: flex;
    flex-direction: column;

    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      display: flex;
      flex-direction: column;
      gap: 8px;

      .new-session-btn {
        width: 100%;
      }
    }

    .session-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;

      .session-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 12px;
        border-radius: 6px;
        cursor: pointer;
        color: rgba(255, 255, 255, 0.65);
        transition: all 0.2s;
        margin-bottom: 2px;

        &:hover {
          background: rgba(255, 255, 255, 0.08);
          color: rgba(255, 255, 255, 0.85);
        }

        &.active {
          background: rgba(64, 158, 255, 0.15);
          color: #409eff;
        }

        .session-title {
          flex: 1;
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .delete-btn {
          opacity: 0;
          transition: opacity 0.2s;
          color: rgba(255, 255, 255, 0.45);

          &:hover {
            color: #f56c6c;
          }
        }

        &:hover .delete-btn {
          opacity: 1;
        }
      }

      .no-sessions {
        padding: 40px 16px;
        text-align: center;
        color: rgba(255, 255, 255, 0.35);
        font-size: 13px;

        p {
          margin: 0 0 4px;
        }

        .hint {
          font-size: 12px;
          opacity: 0.7;
        }
      }
    }
  }

  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #f5f7fa;

    .chat-empty-state {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 24px;

      .brand-area {
        text-align: center;

        h2 {
          font-size: 24px;
          color: #303133;
          margin: 16px 0 8px;
        }

        p {
          font-size: 14px;
          color: #909399;
          margin: 0;
        }
      }
    }

    .chat-input-area {
      padding: 16px 24px;
      background: #fff;
      border-top: 1px solid #e8e8e8;

      :deep(.el-textarea__inner) {
        border-radius: 8px;
        font-size: 14px;
      }

      .input-actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 8px;

        .input-hint {
          font-size: 12px;
          color: #c0c4cc;
        }
      }
    }
  }

  .kb-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
}
</style>
