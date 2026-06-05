<template>
  <el-dialog
    v-model="visible"
    :title="fileName"
    width="80%"
    top="5vh"
    destroy-on-close
    @close="handleClose"
  >
    <div class="preview-container">
      <!-- Loading -->
      <div v-if="loading" class="preview-loading">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="preview-error">
        <p>{{ error }}</p>
      </div>

      <!-- Markdown -->
      <div v-else-if="fileExt === '.md' || fileExt === '.txt'" class="preview-md" v-html="mdHtml" />

      <!-- PDF -->
      <div v-else-if="fileExt === '.pdf'" class="preview-pdf">
        <div v-for="page in pdfPages" :key="page" class="pdf-page">
          <canvas :ref="(el) => setCanvasRef(page, el as HTMLCanvasElement)" />
        </div>
      </div>

      <!-- Image -->
      <img v-else-if="isImage" :src="contentUrl" class="preview-image" />

      <!-- Word -->
      <div v-else-if="fileExt === '.docx' || fileExt === '.doc'" class="preview-docx" v-html="docxHtml" />

      <!-- Unsupported -->
      <div v-else class="preview-unsupported">
        <p>暂不支持预览此文件格式 ({{ fileExt }})</p>
        <el-button type="primary" @click="downloadFile">下载文件</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import DOMPurify from 'dompurify'

const props = defineProps<{
  modelValue: boolean
  fileId: number
  fileName: string
  fileExt: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = ref(props.modelValue)
const loading = ref(false)
const error = ref('')
const contentUrl = ref('')
const mdHtml = ref('')
const docxHtml = ref('')
const pdfPages = ref(0)
const pdfRefs = new Map<number, HTMLCanvasElement>()

const isImage = ['.png', '.jpg', '.jpeg', '.gif', '.bmp'].includes(props.fileExt)

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => { emit('update:modelValue', val) })

watch(visible, async (val) => {
  if (val) await loadContent()
})

function setCanvasRef(page: number, el: HTMLCanvasElement | null) {
  if (el) pdfRefs.set(page, el)
}

function getToken(): string {
  return localStorage.getItem('sa-token') || ''
}

async function loadContent() {
  loading.value = true
  error.value = ''
  const url = `/api/doc/${props.fileId}/content`

  try {
    if (props.fileExt === '.md' || props.fileExt === '.txt') {
      const res = await fetch(url, { headers: { 'sa-token': getToken() } })
      const text = await res.text()
      if (!res.ok) throw new Error(text)
      const { marked } = await import('marked')
      mdHtml.value = DOMPurify.sanitize(await marked(text))
    } else if (props.fileExt === '.pdf') {
      contentUrl.value = url
      await renderPDF(url)
    } else if (props.fileExt === '.docx' || props.fileExt === '.doc') {
      const res = await fetch(url, { headers: { 'sa-token': getToken() } })
      const buffer = await res.arrayBuffer()
      if (!res.ok) throw new Error('load failed')
      const mammoth = await import('mammoth')
      const result = await mammoth.convertToHtml({ arrayBuffer: buffer })
      docxHtml.value = DOMPurify.sanitize(result.value)
    } else if (isImage) {
      contentUrl.value = url
    }
  } catch (e: any) {
    error.value = '预览失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

async function renderPDF(url: string) {
  const pdfjsLib = await import('pdfjs-dist')
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@4.0.379/build/pdf.worker.min.mjs`

  const loadingTask = pdfjsLib.getDocument({
    url,
    httpHeaders: { 'sa-token': getToken() }
  })
  const pdf = await loadingTask.promise
  pdfPages.value = pdf.numPages

  // Render pages after DOM update
  await new Promise(r => setTimeout(r, 100))
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const canvas = pdfRefs.get(i)
    if (!canvas) continue
    const viewport = page.getViewport({ scale: 1.5 })
    canvas.width = viewport.width
    canvas.height = viewport.height
    const ctx = canvas.getContext('2d')!
    await page.render({ canvasContext: ctx, viewport }).promise
  }
}

function downloadFile() {
  const a = document.createElement('a')
  a.href = `/api/doc/${props.fileId}/content?sa-token=${encodeURIComponent(getToken())}`
  a.download = props.fileName
  a.click()
}

function handleClose() {
  mdHtml.value = ''
  docxHtml.value = ''
  pdfPages.value = 0
  pdfRefs.clear()
  contentUrl.value = ''
  error.value = ''
}
</script>

<style scoped lang="scss">
.preview-container {
  min-height: 300px;
  max-height: 75vh;
  overflow: auto;

  .preview-loading, .preview-error, .preview-unsupported {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: #909399;
    gap: 12px;
  }

  .preview-md {
    padding: 20px;
    line-height: 1.8;
    font-size: 15px;
    max-width: 900px;
    margin: 0 auto;

    :deep(h1), :deep(h2), :deep(h3) { margin-top: 24px; }
    :deep(pre) { background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; }
    :deep(code) { font-family: monospace; font-size: 13px; }
    :deep(blockquote) { border-left: 4px solid #409eff; padding-left: 16px; color: #666; margin: 16px 0; }
    :deep(table) { border-collapse: collapse; width: 100%; }
    :deep(th), :deep(td) { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    :deep(img) { max-width: 100%; }
  }

  .preview-pdf {
    .pdf-page {
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      canvas {
        display: block;
        margin: 0 auto;
        max-width: 100%;
        height: auto;
      }
    }
  }

  .preview-docx {
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
    line-height: 1.8;
  }

  .preview-image {
    display: block;
    max-width: 100%;
    margin: 0 auto;
  }
}
</style>
