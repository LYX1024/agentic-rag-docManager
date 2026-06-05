<template>
  <el-card
    class="kb-card"
    :body-style="{ padding: '20px' }"
    shadow="hover"
    @click="handleClick"
  >
    <div class="kb-card-header">
      <el-icon class="kb-icon" :size="28"><Folder /></el-icon>
      <h3 class="kb-name">{{ kb.name }}</h3>
    </div>
    <p class="kb-description">{{ truncatedDescription }}</p>
    <div class="kb-meta">
      <div class="meta-item">
        <el-icon><Document /></el-icon>
        <span>{{ kb.fileCount ?? 0 }} 个文件</span>
      </div>
      <span class="meta-date">{{ formattedDate }}</span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { KnowledgeBase } from '@/api/knowledgeBase'
import { Folder, Document } from '@element-plus/icons-vue'

const props = defineProps<{
  kb: KnowledgeBase
}>()

const emit = defineEmits<{
  (e: 'click', kb: KnowledgeBase): void
}>()

const truncatedDescription = computed(() => {
  const desc = props.kb.description || '暂无描述'
  return desc.length > 60 ? desc.slice(0, 60) + '...' : desc
})

const formattedDate = computed(() => {
  if (!props.kb.createdAt) return '-'
  return new Date(props.kb.createdAt).toLocaleDateString('zh-CN')
})

function handleClick() {
  emit('click', props.kb)
}
</script>

<style scoped lang="scss">
.kb-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e8e8e8;

  &:hover {
    border-color: #409eff;
    transform: translateY(-2px);
  }

  .kb-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;

    .kb-icon {
      color: #409eff;
      flex-shrink: 0;
    }

    .kb-name {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .kb-description {
    font-size: 13px;
    color: #909399;
    line-height: 1.5;
    margin-bottom: 16px;
    min-height: 39px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .kb-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #909399;
    }

    .meta-date {
      font-size: 12px;
      color: #c0c4cc;
    }
  }
}
</style>
