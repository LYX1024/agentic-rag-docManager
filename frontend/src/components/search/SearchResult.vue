<template>
  <el-card class="search-result-card" shadow="hover">
    <div class="result-content">
      <p class="result-text" v-html="highlightedText"></p>
    </div>
    <div class="result-meta">
      <div class="meta-left">
        <el-tag size="small" type="info">
          <el-icon style="margin-right: 2px"><Document /></el-icon>
          {{ result.fileSource }}
        </el-tag>
        <span class="chunk-label">块 #{{ result.chunkIndex }}</span>
      </div>
      <el-tag :type="scoreType" size="small" effect="dark">
        {{ scorePercent }}
      </el-tag>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchResultItem } from '@/api/search'
import { Document } from '@element-plus/icons-vue'

const props = defineProps<{
  result: SearchResultItem
  query?: string
}>()

const scoreType = computed(() => {
  const s = props.result.score
  if (s > 0.7) return 'success'
  if (s > 0.4) return 'warning'
  return 'info'
})

const scorePercent = computed(() => {
  return (props.result.score * 100).toFixed(1) + '%'
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
    text = text.replace(regex, '<mark class="search-highlight">$1</mark>')
  }
  return text
})
</script>

<style scoped lang="scss">
.search-result-card {
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;

  .result-content {
    margin-bottom: 12px;

    .result-text {
      font-size: 14px;
      line-height: 1.8;
      color: #303133;
      margin: 0;

      :deep(.search-highlight) {
        background-color: #fff3cd;
        color: #856404;
        padding: 1px 4px;
        border-radius: 2px;
      }
    }
  }

  .result-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .meta-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .chunk-label {
        font-size: 12px;
        color: #c0c4cc;
      }
    }
  }
}
</style>
