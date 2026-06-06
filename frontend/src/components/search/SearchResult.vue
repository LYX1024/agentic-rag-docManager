<template>
  <div class="bg-white/60 rounded-sm border border-[#d4cdc5]/30 p-5 mb-3 transition-all duration-700 ease-in-out">
    <div class="mb-3">
      <p class="font-mono text-sm leading-relaxed text-[#3d3d3d]" v-html="highlightedText" />
    </div>
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="font-mono text-xs px-2 py-0.5 bg-[#c9a88c]/30 text-[#3d3d3d]">
          {{ result.fileSource }}
        </span>
        <span class="font-mono text-xs text-gray-400">块 #{{ result.chunkIndex }}</span>
      </div>
      <span
        class="font-mono text-xs px-2 py-0.5 border border-[#3d3d3d]"
        :class="scoreClass"
      >
        {{ scorePercent }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchResultItem } from '@/api/search'

const props = defineProps<{
  result: SearchResultItem
  query?: string
}>()

const scorePercent = computed(() => {
  return (props.result.score * 100).toFixed(1) + '%'
})

const scoreClass = computed(() => {
  const s = props.result.score
  if (s > 0.7) return 'bg-[#5a7a6b] text-white'
  if (s > 0.4) return 'bg-[#c9a88c] text-[#3d3d3d]'
  return 'bg-[#f5f0eb] text-[#3d3d3d]'
})

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

const highlightedText = computed(() => {
  let text = escapeHtml(props.result.text)
  if (props.query) {
    const escaped = props.query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escaped})`, 'gi')
    text = text.replace(regex, '<mark class="bg-[#5a7a6b] text-white px-0.5">$1</mark>')
  }
  return text
})
</script>
