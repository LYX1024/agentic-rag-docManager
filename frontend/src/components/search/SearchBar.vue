<template>
  <div class="w-full max-w-[800px] mx-auto">
    <div class="flex border border-[#d4cdc5]/40 bg-white">
      <select
        v-model="searchModeModel"
        class="bg-white border-r border-[#d4cdc5]/40 px-3 py-3 font-light text-sm focus:outline-none cursor-pointer"
      >
        <option value="hybrid">混合搜索</option>
        <option value="vector">向量搜索</option>
        <option value="bm25">关键词</option>
      </select>
      <input
        v-model="queryModel"
        :placeholder="placeholder"
        class="flex-1 bg-transparent focus:outline-none px-4 py-3 font-light text-sm placeholder:text-gray-400"
        @keyup.enter="handleSearch"
      />
      <button
        class="bg-[#5a7a6b] text-[#f5f0eb] font-light tracking-wide text-sm px-6 py-3 hover:opacity-90 transition-colors duration-700 ease-in-out cursor-pointer"
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
