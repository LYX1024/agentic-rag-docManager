<template>
  <div ref="scrollContainer" class="chat-window">
    <div v-if="messages.length === 0 && !loading" class="chat-empty">
      <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
      <p>开始新的对话</p>
    </div>
    <div v-else class="chat-messages">
      <ChatMessage
        v-for="(msg, index) in messages"
        :key="index"
        :message="msg"
      />
      <div v-if="isStreaming" class="streaming-indicator">
        <span class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
        <span class="streaming-text">AI 正在思考...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import type { ChatMessage as ChatMessageType } from '@/api/chat'
import ChatMessage from './ChatMessage.vue'
import { ChatDotRound } from '@element-plus/icons-vue'

const props = defineProps<{
  messages: ChatMessageType[]
  loading?: boolean
  isStreaming?: boolean
}>()

const scrollContainer = ref<HTMLElement>()

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

onMounted(() => {
  scrollToBottom()
})

watch(
  () => props.messages.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => props.messages[props.messages.length - 1]?.content,
  () => {
    scrollToBottom()
  }
)
</script>

<style scoped lang="scss">
.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;

  .chat-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 16px;
    color: #c0c4cc;
    font-size: 14px;
  }

  .chat-messages {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .streaming-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 8px;
    align-self: flex-start;

    .typing-dots {
      display: flex;
      gap: 4px;

      .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #409eff;
        animation: typing-bounce 1.4s ease-in-out infinite;

        &:nth-child(2) {
          animation-delay: 0.2s;
        }
        &:nth-child(3) {
          animation-delay: 0.4s;
        }
      }
    }

    .streaming-text {
      font-size: 13px;
      color: #909399;
    }
  }
}

@keyframes typing-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}
</style>
