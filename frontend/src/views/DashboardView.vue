<template>
  <AppLayout>
    <div class="dashboard">
      <div class="dashboard-header">
        <h1>我的知识库</h1>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          创建知识库
        </el-button>
      </div>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="3" animated />
      </div>

      <div v-else-if="kbList.length === 0" class="empty-container">
        <el-empty description="还没有知识库，点击上方按钮创建">
          <el-button type="primary" @click="showCreateDialog = true">创建知识库</el-button>
        </el-empty>
      </div>

      <div v-else class="kb-grid">
        <KBCard
          v-for="kb in kbList"
          :key="kb.id"
          :kb="kb"
          @click="goToKB"
          @delete="handleDeleteKB"
        />
      </div>

      <CreateKBDialog
        v-model:visible="showCreateDialog"
        @confirm="handleCreate"
      />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useKBStore } from '@/stores/knowledgeBase'
import type { KnowledgeBase, CreateKBParams } from '@/api/knowledgeBase'
import AppLayout from '@/components/layout/AppLayout.vue'
import KBCard from '@/components/kb/KBCard.vue'
import CreateKBDialog from '@/components/kb/CreateKBDialog.vue'

const router = useRouter()
const kbStore = useKBStore()

const loading = ref(true)
const showCreateDialog = ref(false)

const kbList = ref<KnowledgeBase[]>([])

onMounted(async () => {
  await fetchList()
})

async function fetchList() {
  loading.value = true
  try {
    await kbStore.fetchKBList()
    kbList.value = kbStore.kbList
  } catch {
    ElMessage.error('获取知识库列表失败')
  } finally {
    loading.value = false
  }
}

function goToKB(kb: KnowledgeBase) {
  kbStore.setCurrentKB(kb)
  router.push(`/kb/${kb.id}`)
}

async function handleCreate(data: CreateKBParams) {
  try {
    const kb = await kbStore.createKB(data)
    ElMessage.success('知识库创建成功')
    showCreateDialog.value = false
    await fetchList()
  } catch {
    ElMessage.error('创建知识库失败')
  }
}

async function handleDeleteKB(kb: KnowledgeBase) {
  try {
    await kbStore.deleteKB(kb.id)
    ElMessage.success('知识库已删除')
    await fetchList()
  } catch {
    ElMessage.error('删除知识库失败')
  }
}
</script>

<style scoped lang="scss">
.dashboard {
  .dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    h1 {
      font-size: 22px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }

  .loading-container {
    padding: 40px;
  }

  .empty-container {
    margin-top: 60px;
  }

  .kb-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;

    @media (max-width: 1400px) {
      grid-template-columns: repeat(3, 1fr);
    }

    @media (max-width: 1100px) {
      grid-template-columns: repeat(2, 1fr);
    }

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }
}
</style>
