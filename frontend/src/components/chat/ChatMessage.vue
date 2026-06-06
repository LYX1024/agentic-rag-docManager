<template>
  <div :class="['chat-message', message.role]">
    <div class="message-avatar">
      <el-avatar v-if="message.role === 'user'" :size="36" icon="UserFilled" />
      <el-avatar v-else :size="36" icon="Cpu" style="background-color: #409eff" />
    </div>
    <div class="message-body">
      <div class="message-content">
        <div v-if="message.role === 'assistant'" class="message-text markdown-body" v-html="renderedContent" />
        <div v-else class="message-text">{{ message.content }}</div>
      </div>
      <div
        v-if="message.role === 'assistant' && groupedSources.length > 0"
        class="message-sources"
      >
        <el-collapse>
          <el-collapse-item :title="'来源 (' + groupedSources.length + ' 个文档)'" name="1">
            <SourceCitation
              v-for="(group, idx) in groupedSources"
              :key="idx"
              :group="group"
            />
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage as ChatMessageType } from '@/api/chat'
import SourceCitation from './SourceCitation.vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

const props = defineProps<{
  message: ChatMessageType
}>()

const renderedContent = computed(() => {
  if (props.message.role !== 'assistant') return ''
  const html = marked(props.message.content, { async: false }) as string
  return DOMPurify.sanitize(html)
})

const groupedSources = computed(() => {
  const sources = props.message.sources
  if (!sources || !Array.isArray(sources) || sources.length === 0) return []
  const groups: Record<string, { file_name: string; chunks: any[]; bestScore: number }> = {}
  for (const s of sources) {
    const key = s.file_name || 'unknown'
    if (!groups[key]) groups[key] = { file_name: key, chunks: [], bestScore: 0 }
    groups[key].chunks.push(s)
    groups[key].bestScore = Math.max(groups[key].bestScore, s.score || 0)
  }
  return Object.values(groups).sort((a, b) => b.bestScore - a.bestScore)
})
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

      .markdown-body {
        font-size: 14px;
        line-height: 1.8;

        :deep(h1), :deep(h2), :deep(h3), :deep(h4) { margin: 16px 0 8px; font-weight: 600; }
        :deep(h2) { font-size: 17px; border-bottom: 1px solid #e8e8e8; padding-bottom: 4px; }
        :deep(h3) { font-size: 15px; }
        :deep(p) { margin: 8px 0; }
        :deep(ul), :deep(ol) { padding-left: 20px; margin: 8px 0; }
        :deep(li) { margin: 4px 0; }
        :deep(strong) { font-weight: 600; color: #303133; }
        :deep(code) { font-family: monospace; background: #e8e8e8; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
        :deep(pre) { background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 6px; overflow-x: auto; margin: 12px 0; }
        :deep(pre code) { background: transparent; padding: 0; color: inherit; }
        :deep(blockquote) { border-left: 4px solid #409eff; padding-left: 16px; color: #666; margin: 12px 0; }
        :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
        :deep(th), :deep(td) { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        :deep(th) { background: #f5f5f5; }
        :deep(a) { color: #409eff; }
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
