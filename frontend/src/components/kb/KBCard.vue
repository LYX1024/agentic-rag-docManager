<template>
  <div
    class="group p-6 md:p-8 bg-[#F9F6F3] hover:bg-[#f5f0eb] border border-[#d4cdc5]/40 border-l-2 border-l-[#5a7a6b] rounded-sm shadow-sm hover:shadow-md hover:border-[#d4cdc5]/60 transition-colors duration-700 ease-in-out cursor-pointer relative"
    @click="handleClick"
  >
    <!-- Delete button -->
    <button
      class="absolute top-3 right-3 w-6 h-6 flex items-center justify-center rounded-sm font-light text-sm text-[#a89279] opacity-0 group-hover:opacity-100 transition-opacity duration-700 cursor-pointer z-10 hover:text-[#607683]"
      @click.stop="handleDelete"
    >
      &times;
    </button>

    <!-- Name -->
    <h3 class="text-lg font-light text-[#3d3d3d] mb-3 tracking-wide truncate group-hover:text-[#5a7a6b] transition-colors duration-700">
      {{ kb.name }}
    </h3>

    <!-- Description -->
    <p class="text-sm font-light text-[#a89279] leading-relaxed mb-6 min-h-[2.5em] group-hover:text-[#8a7660] transition-colors duration-700">
      {{ truncatedDescription }}
    </p>

    <!-- Meta divider -->
    <div class="flex items-center justify-between pt-4 border-t border-[#d4cdc5]/20">
      <span class="text-xs font-light text-[#a89279]">{{ kb.fileCount ?? 0 }} 个文件</span>
      <span class="text-xs font-light text-[#a89279]/60">{{ formattedDate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { KnowledgeBase } from '@/api/knowledgeBase'

const props = defineProps<{
  kb: KnowledgeBase
}>()

const emit = defineEmits<{
  (e: 'click', kb: KnowledgeBase): void
  (e: 'delete', kb: KnowledgeBase): void
}>()

function handleClick() { emit('click', props.kb) }
function handleDelete() { emit('delete', props.kb) }

const truncatedDescription = computed(() => {
  const desc = props.kb.description || 'No description'
  return desc.length > 60 ? desc.slice(0, 60) + '...' : desc
})

const formattedDate = computed(() => {
  if (!props.kb.createdAt) return ''
  return new Date(props.kb.createdAt).toLocaleDateString('zh-CN')
})
</script>
