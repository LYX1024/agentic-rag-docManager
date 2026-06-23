<template>
  <div :class="['flex gap-3 px-2', message.role === 'user' ? 'flex-row-reverse' : '']">
    <!-- Avatar -->
    <div class="flex-shrink-0 pt-1">
      <div
        :class="[
          'w-9 h-9 flex items-center justify-center font-light text-sm border border-[#3d3d3d]',
          message.role === 'user' ? 'bg-[#3d3d3d] text-[#f5f0eb]' : 'bg-[#f5f0eb] border border-[#d4cdc5]/40 text-[#3d3d3d]'
        ]"
      >
        {{ message.role === 'user' ? 'U' : 'AI' }}
      </div>
    </div>

    <!-- Body -->
    <div :class="['flex flex-col gap-2', message.role === 'user' ? 'items-end' : 'items-start', 'max-w-[75%]']">
      <!-- Content -->
      <div
        :class="[
          'p-4 rounded-sm',
          message.role === 'user'
            ? 'bg-[#3d3d3d] text-[#f5f0eb]'
            : 'bg-[#f5f0eb] border border-[#d4cdc5]/40 text-[#3d3d3d]'
        ]"
      >
        <div
          v-if="message.role === 'assistant'"
          class="font-light text-sm leading-relaxed markdown-body"
          v-html="renderedContent"
        />
        <div v-else class="font-light text-sm leading-relaxed whitespace-pre-wrap break-words">
          {{ message.content }}
        </div>
      </div>

      <!-- Sources -->
      <div
        v-if="message.role === 'assistant' && groupedSources.length > 0"
        class="w-full"
      >
        <details class="font-light text-xs">
          <summary class="cursor-pointer text-gray-500 py-1 hover:text-[#3d3d3d] transition-colors duration-700 ease-in-out">
            来源 ({{ groupedSources.length }} 个文档)
          </summary>
          <div class="mt-2 flex flex-col gap-2">
            <SourceCitation
              v-for="(group, idx) in groupedSources"
              :key="idx"
              :group="group"
            />
          </div>
        </details>
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

<style scoped>
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 16px 0 8px;
  font-weight: 300;
  letter-spacing: 0.05em;
  line-height: 1.3;
}
.markdown-body :deep(h1) {
  font-size: 22px;
  border-bottom: 2px solid #3d3d3d;
  padding-bottom: 6px;
}
.markdown-body :deep(h2) {
  font-size: 18px;
  border-bottom: 1px solid #d4cdc5;
  padding-bottom: 4px;
}
.markdown-body :deep(h3) { font-size: 16px; }
.markdown-body :deep(h4) { font-size: 14px; }
.markdown-body :deep(h5) { font-size: 13px; }
.markdown-body :deep(h6) { font-size: 12px; color: #a89279; }
.markdown-body :deep(p) { margin: 8px 0; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: 20px; margin: 8px 0; }
.markdown-body :deep(li) { margin: 4px 0; }
.markdown-body :deep(strong) { font-weight: 500; color: #3d3d3d; }
.markdown-body :deep(em) { font-style: italic; color: #5a7a6b; }
.markdown-body :deep(strong em),
.markdown-body :deep(em strong) { font-weight: 500; font-style: italic; color: #3d3d3d; }
.markdown-body :deep(code) {
  font-family: 'Courier New', Courier, monospace;
  background: #e8e8e8;
  padding: 2px 6px;
  font-size: 12px;
}
.markdown-body :deep(pre) {
  background: #3d3d3d;
  color: #f8f8f2;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}
.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #3d3d3d;
  padding-left: 16px;
  color: #666;
  margin: 12px 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #3d3d3d;
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) { background: #f5f5f5; }
.markdown-body :deep(a) { color: #5a7a6b; }
</style>
