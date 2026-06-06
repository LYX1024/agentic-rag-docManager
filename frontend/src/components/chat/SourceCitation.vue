<template>
  <div class="bg-white border border-[#d4cdc5]/40 p-3">
    <div class="flex items-center gap-2 flex-wrap mb-2">
      <span class="font-light text-xs text-[#3d3d3d]">{{ group.file_name }}</span>
      <span
        class="font-light text-[10px] px-1.5 py-0.5 border border-[#d4cdc5]/40"
        :class="scoreClass"
      >
        {{ percent }}%
      </span>
      <span class="font-light text-[10px] text-gray-400">
        命中 {{ group.chunks.length }} 个分块：{{ chunkIndices }}
      </span>
    </div>
    <div class="border-t border-dashed border-[#d4cdc5]/40 pt-2 flex flex-col gap-1">
      <div v-for="chunk in group.chunks" :key="chunk.chunk_index" class="font-light text-xs text-gray-600 leading-relaxed">
        <span class="text-[#5a7a6b]">[块{{ chunk.chunk_index }}]</span>
        <span>{{ truncate(chunk.chunk_text || chunk.text || '') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  group: {
    file_name: string
    chunks: any[]
    bestScore: number
  }
}>()

const scoreClass = computed(() => {
  const s = props.group.bestScore
  if (s > 0.7) return 'bg-[#5a7a6b] text-white'
  if (s > 0.4) return 'bg-[#c9a88c] text-[#3d3d3d]'
  return 'bg-[#f5f0eb] text-[#3d3d3d]'
})

const percent = computed(() => (props.group.bestScore * 100).toFixed(0))

const chunkIndices = computed(() =>
  props.group.chunks.map((c: any) => c.chunk_index).sort((a: number, b: number) => a - b).join(', ')
)

function truncate(text: string): string {
  return text.length > 120 ? text.slice(0, 120) + '...' : text
}
</script>
