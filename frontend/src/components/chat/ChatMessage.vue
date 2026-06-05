<template>
  <div :class="['chat-message', message.role]">
    <div class="message-avatar">
      <el-avatar v-if="message.role === 'user'" :size="36" icon="UserFilled" />
      <el-avatar v-else :size="36" icon="Cpu" style="background-color: #409eff" />
    </div>
    <div class="message-body">
      <div class="message-content">
        <div class="message-text">{{ message.content }}</div>
      </div>
      <div
        v-if="message.role === 'assistant' && message.sources && message.sources.length > 0"
        class="message-sources"
      >
        <el-collapse>
          <el-collapse-item title="来源" name="1">
            <SourceCitation
              v-for="(source, idx) in message.sources"
              :key="idx"
              :source="source"
            />
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage as ChatMessageType } from '@/api/chat'
import SourceCitation from './SourceCitation.vue'

defineProps<{
  message: ChatMessageType
}>()
</script>

<style scoped lang="scss">
.chat-message {
  display: flex;
  gap: 12px;
  padding: 0 8px;

  .message-avatar {
    flex-shrink: 0;
    padding-top: 4px;
  }

  .message-body {
    max-width: 75%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &.user {
    flex-direction: row-reverse;

    .message-content {
      background-color: #409eff;
      color: #fff;
      border-radius: 12px 12px 4px 12px;

      .message-text {
        font-size: 14px;
        line-height: 1.7;
        white-space: pre-wrap;
        word-break: break-word;
      }
    }
  }

  &.assistant {
    .message-content {
      background-color: #f5f7fa;
      color: #303133;
      border-radius: 12px 12px 12px 4px;
      border: 1px solid #ebeef5;

      .message-text {
        font-size: 14px;
        line-height: 1.8;
        white-space: pre-wrap;
        word-break: break-word;
      }
    }
  }

  .message-content {
    padding: 12px 16px;
    max-width: 100%;
  }

  .message-sources {
    :deep(.el-collapse) {
      border-top: none;
      border-bottom: none;

      .el-collapse-item__header {
        font-size: 12px;
        color: #909399;
        height: 32px;
        line-height: 32px;
        background: transparent;
        border-bottom: none;
        padding-left: 4px;
      }

      .el-collapse-item__wrap {
        border-bottom: none;
        background: transparent;
      }

      .el-collapse-item__content {
        padding: 4px;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
    }
  }
}
</style>
