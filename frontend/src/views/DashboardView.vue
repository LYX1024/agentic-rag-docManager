<template>
  <AppLayout>
    <div class="px-6 md:px-12 py-8 max-w-6xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <h1 class="font-light tracking-wide text-2xl">我的知识库</h1>
        <AppButton variant="primary" @click="showCreateDialog = true">
          创建知识库
        </AppButton>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="p-10 font-mono text-sm text-gray-500">
        加载中...
      </div>

      <!-- Empty -->
      <div v-else-if="kbList.length === 0" class="flex flex-col items-center justify-center py-20 gap-4">
        <p class="font-light tracking-wide text-lg text-gray-500">还没有知识库</p>
        <AppButton variant="secondary" @click="showCreateDialog = true">
          创建知识库
        </AppButton>
      </div>

      <!-- Grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <KBCard
          v-for="kb in kbList"
          :key="kb.id"
          :kb="kb"
          @click="goToKB"
          @delete="handleDeleteKB"
        />
      </div>

      <!-- Create Dialog -->
      <CreateKBDialog
        :visible="showCreateDialog"
        @update:visible="showCreateDialog = $event"
        @confirm="handleCreate"
      />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKBStore } from '@/stores/knowledgeBase'
import type { KnowledgeBase, CreateKBParams } from '@/api/knowledgeBase'
import { Toast } from '@/utils/toast'
import AppLayout from '@/components/layout/AppLayout.vue'
import AppButton from '@/components/ui/AppButton.vue'
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
    Toast.error('获取知识库列表失败')
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
    await kbStore.createKB(data)
    Toast.success('知识库创建成功')
    showCreateDialog.value = false
    await fetchList()
  } catch {
    Toast.error('创建知识库失败')
  }
}

async function handleDeleteKB(kb: KnowledgeBase) {
  try {
    await kbStore.deleteKB(kb.id)
    Toast.success('知识库已删除')
    await fetchList()
  } catch {
    Toast.error('删除知识库失败')
  }
}
</script>
