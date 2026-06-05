<template>
  <div class="source-citation">
    <div class="source-header">
      <el-icon><Document /></el-icon>
      <span class="source-filename">{{ source.file_name }}</span>
      <el-tag size="small" :type="scoreType">
        相似度 {{ (source.score * 100).toFixed(0) }}%
      </el-tag>
    </div>
    <div class="source-body">
      <p class="source-text">{{ truncatedText }}</p>
    </div>
    <div class="source-footer">
      <span class="chunk-info">分块 #{{ source.chunk_index }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatSource } from '@/api/chat'
import { Document } from '@element-plus/icons-vue'

const props = defineProps<{
  source: ChatSource
}>()

const scoreType = computed(() => {
  const s = props.source.score
  if (s > 0.7) return 'success'
  if (s > 0.4) return 'warning'
  return 'info'
})

const truncatedText = computed(() => {
  const text = props.source.text || ''
  return text.length > 150 ? text.slice(0, 150) + '...' : text
})
</script>

<style scoped lang="scss">
.source-citation {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 10px 12px;

  .source-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;

    .source-filename {
      font-size: 13px;
      font-weight: 500;
      color: #303133;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .source-body {
    .source-text {
      font-size: 12px;
      color: #606266;
      line-height: 1.6;
      margin: 0;
    }
  }

  .source-footer {
    margin-top: 6px;

    .chunk-info {
      font-size: 11px;
      color: #c0c4cc;
    }
  }
}
</style>
