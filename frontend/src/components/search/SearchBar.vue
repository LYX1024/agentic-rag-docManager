<template>
  <div class="search-bar">
    <el-input
      v-model="queryModel"
      :placeholder="placeholder"
      size="large"
      clearable
      @keyup.enter="handleSearch"
    >
      <template #prepend>
        <el-select
          v-model="searchModeModel"
          style="width: 120px"
        >
          <el-option label="混合搜索" value="hybrid" />
          <el-option label="向量搜索" value="vector" />
          <el-option label="关键词" value="bm25" />
        </el-select>
      </template>
      <template #append>
        <el-button type="primary" :icon="Search" @click="handleSearch" :loading="loading">
          搜索
        </el-button>
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps<{
  query: string
  searchMode: string
  placeholder?: string
  loading?: boolean
}>()

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

<style scoped lang="scss">
.search-bar {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}
</style>
