<template>
  <div class="source-group">
    <div class="group-header">
      <el-icon><Document /></el-icon>
      <span class="group-filename">{{ group.file_name }}</span>
      <el-tag size="small" :type="scoreType">
        相似度 {{ percent }}%
      </el-tag>
      <span class="chunk-list">命中 {{ group.chunks.length }} 个分块：{{ chunkIndices }}</span>
    </div>
    <div class="group-chunks">
      <div v-for="chunk in group.chunks" :key="chunk.chunk_index" class="chunk-item">
        <span class="chunk-label">[块{{ chunk.chunk_index }}]</span>
        <span class="chunk-text">{{ truncate(chunk.chunk_text || chunk.text || '') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'

const props = defineProps<{
  group: {
    file_name: string
    chunks: any[]
    bestScore: number
  }
}>()

const scoreType = computed(() => {
  const s = props.group.bestScore
  if (s > 0.7) return 'success'
  if (s > 0.4) return 'warning'
  return 'info'
})

const percent = computed(() => (props.group.bestScore * 100).toFixed(0))

const chunkIndices = computed(() =>
  props.group.chunks.map((c: any) => c.chunk_index).sort((a: number, b: number) => a - b).join(', ')
)

function truncate(text: string): string {
  return text.length > 120 ? text.slice(0, 120) + '...' : text
}
</script>

<style scoped lang="scss">
.source-group {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 10px 12px;

  .group-header {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 6px;

    .group-filename {
      font-size: 13px;
      font-weight: 500;
      color: #303133;
    }

    .chunk-list {
      font-size: 11px;
      color: #c0c4cc;
    }
  }

  .group-chunks {
    border-top: 1px dashed #ebeef5;
    padding-top: 6px;

    .chunk-item {
      font-size: 12px;
      color: #606266;
      line-height: 1.6;
      padding: 2px 0;

      .chunk-label {
        color: #409eff;
        font-weight: 500;
        margin-right: 4px;
        white-space: nowrap;
      }
    }
  }
}
</style>
