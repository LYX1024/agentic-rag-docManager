<template>
  <AppLayout>
    <div class="kb-detail">
      <div class="detail-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
          <h1>{{ kbName }}</h1>
        </div>
        <div class="header-right">
          <el-select
            v-model="filterCategory"
            placeholder="全部分类"
            clearable
            style="width: 160px; margin-right: 12px"
            @change="handleCategoryChange"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索知识库文件..."
            :prefix-icon="Search"
            style="width: 260px"
            clearable
            @keyup.enter="handleSearchInKB"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearchInKB" />
            </template>
          </el-input>
        </div>
      </div>

      <div class="upload-section">
        <div class="upload-row">
          <el-input
            v-model="uploadCategory"
            placeholder="输入分类（可选，如：技术文档、合同）"
            style="width: 220px; margin-right: 12px"
            clearable
          />
          <el-upload
            ref="uploadRef"
            class="upload-area"
            :http-request="customUpload"
            :show-file-list="false"
            drag
            multiple
          >
            <el-icon class="upload-icon" :size="48"><UploadFilled /></el-icon>
            <div class="upload-text">
              <p class="upload-title">将文件拖到此处，或点击上传</p>
              <p class="upload-hint">支持 PDF、Word、Excel、TXT、Markdown 等格式文件</p>
            </div>
          </el-upload>
        </div>
      </div>

      <el-card class="file-table-card">
        <template #header>
          <span>文件列表 ({{ total }})</span>
        </template>
        <el-table
          :data="fileList"
          v-loading="tableLoading"
          style="width: 100%"
          stripe
        >
          <el-table-column prop="fileName" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column prop="category" label="分类" width="120" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.category" size="small" type="success">{{ row.category }}</el-tag>
              <span v-else class="no-category">-</span>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="110" align="center">
            <template #default="{ row }">
              {{ formatFileSize(row.fileSize) }}
            </template>
          </el-table-column>
          <el-table-column prop="fileExt" label="类型" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ (row.fileExt || '').replace('.', '').toUpperCase() || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" width="160" align="center">
            <template #default="{ row }">
              {{ formatDate(row.createdAt) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" :icon="View" text @click="handlePreview(row)">
                预览
              </el-button>
              <el-popconfirm
                title="确定要删除该文件吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="handleDelete(row)"
              >
                <template #reference>
                  <el-button type="danger" size="small" :icon="Delete" text>
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrapper" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>

      <PreviewDialog
        v-model="previewVisible"
        :file-id="previewFileId"
        :file-name="previewFileName"
        :file-ext="previewFileExt"
      />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { ArrowLeft, Search, UploadFilled, Delete, View } from '@element-plus/icons-vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PreviewDialog from '@/components/kb/PreviewDialog.vue'
import * as documentApi from '@/api/document'
import type { Document, DocumentStatus } from '@/api/document'
import * as kbApi from '@/api/knowledgeBase'

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
    ElMessage.error('获取文件列表失败')
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

async function customUpload(options: UploadRequestOptions) {
  try {
    const category = uploadCategory.value || undefined
    await documentApi.uploadFile(kbId, options.file, category)
    ElMessage.success('文件上传成功')
    currentPage.value = 1
    uploadCategory.value = ''
    await fetchFileList()
    await fetchCategories()
  } catch {
    ElMessage.error('文件上传失败')
  }
}

function handleCategoryChange() {
  currentPage.value = 1
  fetchFileList()
}

function statusType(status: DocumentStatus): string {
  const map: Record<DocumentStatus, string> = {
    UPLOADED: 'info',
    PARSING: 'warning',
    CHUNKING: 'warning',
    EMBEDDING: 'warning',
    COMPLETED: 'success',
    FAILED: 'danger'
  }
  return map[status] || 'info'
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

async function handleDelete(row: Document) {
  try {
    await documentApi.deleteDoc(row.id)
    ElMessage.success('删除成功')
    fetchFileList()
    fetchCategories()
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped lang="scss">
.kb-detail {
  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      h1 {
        font-size: 22px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .upload-section {
    margin-bottom: 24px;

    .upload-row {
      display: flex;
      align-items: stretch;

      .upload-area {
        flex: 1;

        :deep(.el-upload-dragger) {
          width: 100%;
          padding: 24px;
          border: 2px dashed #d9d9d9;
          border-radius: 8px;
          transition: border-color 0.3s;

          &:hover {
            border-color: #409eff;
          }
        }
      }
    }

    .upload-icon {
      color: #c0c4cc;
      margin-bottom: 8px;
    }

    .upload-text {
      .upload-title {
        font-size: 14px;
        color: #606266;
        margin: 0 0 4px;
      }

      .upload-hint {
        font-size: 12px;
        color: #c0c4cc;
        margin: 0;
      }
    }
  }

  .file-table-card {
    .no-category {
      color: #c0c4cc;
    }

    .pagination-wrapper {
      display: flex;
      justify-content: flex-end;
      margin-top: 16px;
    }
  }
}
</style>
