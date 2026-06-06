<template>
  <AppLayout>
    <div class="px-6 md:px-12 py-8 max-w-7xl mx-auto" @dragenter.prevent @dragover.prevent @drop.prevent>
      <!-- Header -->
      <div class="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div class="flex items-center gap-4">
          <AppButton variant="secondary" size="sm" @click="goBack">
            ← 返回
          </AppButton>
          <h1 class="font-light tracking-wide text-2xl">{{ kbName }}</h1>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <AppSelect
            v-model="filterCategory"
            :options="categoryOptions"
            placeholder="全部分类"
          />
          <input
            v-model="searchKeyword"
            placeholder="搜索知识库文件..."
            class="bg-white border-2 border-[#3d3d3d] focus:outline-none px-3 py-2 font-mono text-sm w-[260px] placeholder:text-gray-400"
            @keyup.enter="handleSearchInKB"
          />
        </div>
      </div>

      <!-- Upload Section -->
      <div class="mb-6 flex items-stretch gap-3">
        <input
          v-model="uploadCategory"
          placeholder="输入分类（可选）"
          class="bg-white border-2 border-[#3d3d3d] focus:outline-none px-3 py-2 font-mono text-sm w-[220px] flex-shrink-0 placeholder:text-gray-400"
        />
        <div
          class="flex-1 border-2 border-dashed border-[#3d3d3d] bg-white flex flex-col items-center justify-center p-6 cursor-pointer hover:border-[#5a7a6b] transition-colors"
          @click="triggerFileInput"
          @drop.prevent="handleDrop"
        >
          <span class="text-3xl mb-2"></span>
          <p class="font-mono text-sm text-[#3d3d3d]">将文件拖到此处，或点击上传</p>
          <p class="font-mono text-xs text-gray-400 mt-1">支持 PDF、Word、Excel、TXT、Markdown 等格式</p>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />
      </div>

      <!-- File Table Card -->
      <div class="bg-white border-2 border-[#3d3d3d] shadow-[4px_4px_0px_0px_rgba(61,61,61,0.10)]">
        <div class="border-b-2 border-[#3d3d3d] px-4 py-3 font-mono text-sm">
          文件列表 ({{ total }})
        </div>
        <div v-if="tableLoading" class="p-10 text-center font-mono text-sm text-gray-500">
          加载中...
        </div>
        <div v-else-if="fileList.length === 0" class="p-10 text-center font-mono text-sm text-gray-500">
          暂无文件
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full font-mono text-sm">
            <thead>
              <tr class="border-b-2 border-[#3d3d3d] bg-gray-50">
                <th class="text-left px-4 py-2 font-mono text-xs">文件名</th>
                <th class="text-center px-4 py-2 font-mono text-xs">分类</th>
                <th class="text-center px-4 py-2 font-mono text-xs">大小</th>
                <th class="text-center px-4 py-2 font-mono text-xs">类型</th>
                <th class="text-center px-4 py-2 font-mono text-xs">状态</th>
                <th class="text-center px-4 py-2 font-mono text-xs">上传时间</th>
                <th class="text-center px-4 py-2 font-mono text-xs">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in fileList"
                :key="row.id"
                :class="['border-b border-gray-200', idx % 2 === 0 ? 'bg-white' : 'bg-gray-50']"
              >
                <td class="px-4 py-2 max-w-[200px] truncate" :title="row.fileName">
                  {{ row.fileName }}
                </td>
                <td class="text-center px-4 py-2">
                  <span v-if="row.category" class="bg-[#3d3d3d] text-white text-xs px-2 py-0.5">
                    {{ row.category }}
                  </span>
                  <span v-else class="text-gray-400">-</span>
                </td>
                <td class="text-center px-4 py-2 text-xs text-gray-500">
                  {{ formatFileSize(row.fileSize) }}
                </td>
                <td class="text-center px-4 py-2">
                  <span class="text-xs border border-[#3d3d3d] px-1.5 py-0.5">
                    {{ (row.fileExt || '').replace('.', '').toUpperCase() || '-' }}
                  </span>
                </td>
                <td class="text-center px-4 py-2">
                  <span
                    class="text-xs px-1.5 py-0.5 border border-[#3d3d3d]"
                    :class="statusClass(row.status)"
                  >
                    {{ statusLabel(row.status) }}
                  </span>
                </td>
                <td class="text-center px-4 py-2 text-xs text-gray-500">
                  {{ formatDate(row.createdAt) }}
                </td>
                <td class="text-center px-4 py-2">
                  <div class="flex items-center justify-center gap-2">
                    <button
                      class="font-mono text-xs text-[#3d3d3d] hover:text-[#5a7a6b] transition-colors cursor-pointer underline"
                      @click="handlePreview(row)"
                    >
                      预览
                    </button>
                    <button
                      class="font-mono text-xs text-[#5a7a6b] hover:text-[#3d3d3d] transition-colors cursor-pointer underline"
                      @click="confirmDelete(row)"
                    >
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Pagination -->
        <div v-if="total > pageSize" class="flex items-center justify-end px-4 py-3 border-t-2 border-[#3d3d3d] gap-2">
          <span class="font-mono text-xs text-gray-500">共 {{ total }} 条</span>
          <button
            class="font-mono text-xs border border-[#3d3d3d] px-2 py-1 hover:bg-[#3d3d3d] hover:text-white transition-colors cursor-pointer disabled:opacity-30"
            :disabled="currentPage <= 1"
            @click="handlePageChange(currentPage - 1)"
          >
            上一页
          </button>
          <span class="font-mono text-xs">{{ currentPage }} / {{ totalPages }}</span>
          <button
            class="font-mono text-xs border border-[#3d3d3d] px-2 py-1 hover:bg-[#3d3d3d] hover:text-white transition-colors cursor-pointer disabled:opacity-30"
            :disabled="currentPage >= totalPages"
            @click="handlePageChange(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>

      <!-- Preview Dialog -->
      <PreviewDialog
        :model-value="previewVisible"
        :file-id="previewFileId"
        :file-name="previewFileName"
        :file-ext="previewFileExt"
        @update:model-value="previewVisible = $event"
      />

      <!-- Delete Confirm Dialog -->
      <AppDialog
        :model-value="deleteDialogVisible"
        title="确认删除"
        width="400px"
        @update:model-value="deleteDialogVisible = $event"
      >
        <p class="font-mono text-sm">确定要删除该文件吗？此操作不可撤销。</p>
        <template #footer>
          <AppButton variant="secondary" @click="deleteDialogVisible = false">取消</AppButton>
          <AppButton variant="danger" @click="executeDelete">确定删除</AppButton>
        </template>
      </AppDialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Document, DocumentStatus } from '@/api/document'
import * as documentApi from '@/api/document'
import * as kbApi from '@/api/knowledgeBase'
import { Toast } from '@/utils/toast'
import AppLayout from '@/components/layout/AppLayout.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import PreviewDialog from '@/components/kb/PreviewDialog.vue'

const route = useRoute()
const router = useRouter()

const kbId = Number(route.params.id)
const kbName = ref('')

const fileList = ref<Document[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const tableLoading = ref(false)
const searchKeyword = ref('')
const filterCategory = ref('')
const uploadCategory = ref('')
const categories = ref<string[]>([])
const previewVisible = ref(false)
const previewFileId = ref(0)
const previewFileName = ref('')
const previewFileExt = ref('')
const deleteDialogVisible = ref(false)
const deleteTarget = ref<Document | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const categoryOptions = computed(() => {
  const opts = categories.value.map(c => ({ label: c, value: c }))
  return [{ label: '全部分类', value: '' }, ...opts]
})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

onMounted(async () => {
  await fetchKBInfo()
  await fetchFileList()
  await fetchCategories()
})

async function fetchKBInfo() {
  try {
    const res = await kbApi.getKB(kbId)
    kbName.value = res.data.name
  } catch {
    kbName.value = '知识库'
  }
}

async function fetchFileList() {
  tableLoading.value = true
  try {
    const category = filterCategory.value || undefined
    const res = await documentApi.listDocs(kbId, category, currentPage.value - 1, pageSize.value)
    fileList.value = res.data.records || []
    total.value = res.data.total || 0
  } catch {
    Toast.error('获取文件列表失败')
  } finally {
    tableLoading.value = false
  }
}

async function fetchCategories() {
  try {
    const res = await documentApi.getCategories(kbId)
    categories.value = res.data || []
  } catch {
    // non-critical
  }
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) {
    for (let i = 0; i < input.files.length; i++) {
      uploadFile(input.files[i])
    }
    input.value = ''
  }
}

function handleDrop(event: DragEvent) {
  if (event.dataTransfer?.files) {
    for (let i = 0; i < event.dataTransfer.files.length; i++) {
      uploadFile(event.dataTransfer.files[i])
    }
  }
}

async function uploadFile(file: File) {
  try {
    const category = uploadCategory.value || undefined
    await documentApi.uploadFile(kbId, file, category)
    Toast.success(`文件 "${file.name}" 上传成功`)
    currentPage.value = 1
    uploadCategory.value = ''
    await fetchFileList()
    await fetchCategories()
  } catch {
    Toast.error(`文件 "${file.name}" 上传失败`)
  }
}

function statusClass(status: DocumentStatus): string {
  const map: Record<DocumentStatus, string> = {
    UPLOADED: 'bg-gray-200 text-[#3d3d3d]',
    PARSING: 'bg-white text-[#3d3d3d]',
    CHUNKING: 'bg-white text-[#3d3d3d]',
    EMBEDDING: 'bg-white text-[#3d3d3d]',
    COMPLETED: 'bg-[#3d3d3d] text-white',
    FAILED: 'bg-[#5a7a6b] text-white'
  }
  return map[status] || 'bg-gray-200 text-[#3d3d3d]'
}

function statusLabel(status: DocumentStatus): string {
  const map: Record<DocumentStatus, string> = {
    UPLOADED: '已上传',
    PARSING: '解析中',
    CHUNKING: '分块中',
    EMBEDDING: '向量化中',
    COMPLETED: '已完成',
    FAILED: '失败'
  }
  return map[status] || status
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let idx = 0
  let size = bytes
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx++
  }
  return size.toFixed(idx === 0 ? 0 : 1) + ' ' + units[idx]
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function goBack() {
  router.push('/dashboard')
}

function handleSearchInKB() {
  if (searchKeyword.value.trim()) {
    router.push(`/search/${kbId}?q=${encodeURIComponent(searchKeyword.value)}`)
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchFileList()
}

function handlePreview(row: Document) {
  previewFileId.value = row.id
  previewFileName.value = row.fileName
  previewFileExt.value = row.fileExt
  previewVisible.value = true
}

function confirmDelete(row: Document) {
  deleteTarget.value = row
  deleteDialogVisible.value = true
}

async function executeDelete() {
  if (!deleteTarget.value) return
  try {
    await documentApi.deleteDoc(deleteTarget.value.id)
    Toast.success('删除成功')
    deleteDialogVisible.value = false
    deleteTarget.value = null
    fetchFileList()
    fetchCategories()
  } catch {
    Toast.error('删除失败')
  }
}

// Watch category filter
watch(filterCategory, () => {
  currentPage.value = 1
  fetchFileList()
})
</script>
