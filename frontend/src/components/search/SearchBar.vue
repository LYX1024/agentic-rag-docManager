<template>
  <div class="w-full max-w-[800px] mx-auto">
    <div class="flex border-2 border-[#3d3d3d] bg-white">
      <select
        v-model="searchModeModel"
        class="bg-white border-r-2 border-[#3d3d3d] px-3 py-3 font-mono text-sm focus:outline-none cursor-pointer"
      >
        <option value="hybrid">混合搜索</option>
        <option value="vector">向量搜索</option>
        <option value="bm25">关键词</option>
      </select>
      <input
        v-model="queryModel"
        :placeholder="placeholder"
        class="flex-1 bg-transparent focus:outline-none px-4 py-3 font-mono text-sm placeholder:text-gray-400"
        @keyup.enter="handleSearch"
      />
      <button
        class="bg-[#3d3d3d] text-white font-mono text-sm px-6 py-3 hover:bg-[#5a7a6b] transition-colors duration-300 cursor-pointer"
        :disabled="loading"
        @click="handleSearch"
      >
        {{ loading ? '搜索中...' : '搜索' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  query: string
  searchMode: string
  placeholder?: string
  loading?: boolean
}>(), {
  placeholder: '请输入搜索内容...',
  loading: false
})

const emit = defineEmits<{
  (e: 'update:query', value: string): void
  (e: 'update:searchMode', value: string): void
  (e: 'search'): void
}>()

const queryModel = computed({
  get: () => props.query,
  set: (v: string) => emit('update:query', v)
})

const searchModeModel = computed({
  get: () => props.searchMode,
  set: (v: string) => emit('update:searchMode', v)
})

function handleSearch() {
  if (queryModel.value.trim()) {
    emit('search')
  }
}
</script>
