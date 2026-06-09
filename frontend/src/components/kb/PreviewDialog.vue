<template>
  <AppDialog
    :model-value="visible"
    :title="fileName"
    width="80%"
    @update:model-value="onVisibleChange"
  >
    <div class="min-h-[300px] max-h-[70vh] overflow-auto">
      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center min-h-[200px] text-gray-500 font-light gap-3">
        <span class="text-lg animate-pulse">⋯</span>
        <p>加载中...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="flex flex-col items-center justify-center min-h-[200px] text-[#5a7a6b] font-light gap-3">
        <p>{{ error }}</p>
      </div>

      <!-- Markdown -->
      <div
        v-else-if="fileExt === '.md' || fileExt === '.txt'"
        class="p-5 leading-relaxed text-sm max-w-[900px] mx-auto font-light markdown-body"
        v-html="mdHtml"
      />

      <!-- PDF -->
      <div v-else-if="fileExt === '.pdf'" class="preview-pdf">
        <div v-for="page in pdfPages" :key="page" class="mb-4 border border-[#d4cdc5]/40">
          <canvas :ref="(el) => setCanvasRef(page, el as HTMLCanvasElement)" class="block mx-auto max-w-full h-auto" />
        </div>
      </div>

      <!-- Image -->
      <img v-else-if="isImage" :src="contentUrl" class="block max-w-full mx-auto" />

      <!-- Word -->
      <div
        v-else-if="fileExt === '.docx' || fileExt === '.doc'"
        class="p-5 max-w-[900px] mx-auto leading-relaxed docx-body"
        v-html="docxHtml"
      />

      <!-- Unsupported -->
      <div v-else class="flex flex-col items-center justify-center min-h-[200px] text-gray-500 font-light gap-3">
        <p>暂不支持预览此文件格式 ({{ fileExt }})</p>
        <AppButton variant="secondary" @click="downloadFile">下载文件</AppButton>
      </div>
    </div>
  </AppDialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DOMPurify from 'dompurify'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppButton from '@/components/ui/AppButton.vue'

const props = defineProps<{
  modelValue: boolean
  fileId: number
  fileName: string
  fileExt: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const visible = ref(props.modelValue)
const loading = ref(false)
const error = ref('')
const contentUrl = ref('')
const mdHtml = ref('')
const docxHtml = ref('')
const pdfPages = ref(0)
const pdfRefs = new Map<number, HTMLCanvasElement>()

const isImage = computed(() => ['.png', '.jpg', '.jpeg', '.gif', '.bmp'].includes(props.fileExt))

watch(() => props.modelValue, (val) => { visible.value = val })

function onVisibleChange(val: boolean) {
  visible.value = val
  emit('update:modelValue', val)
}

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
    } else if (isImage.value) {
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

  await new Promise(r => setTimeout(r, 100))
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const canvas = pdfRefs.get(i)
    if (!canvas) continue
    const viewport = page.getViewport({ scale: 1.5 })
    canvas.width = viewport.width
    canvas.height = viewport.height
    const ctx = canvas.getContext('2d')!
    await page.render({ canvas, canvasContext: ctx, viewport }).promise
  }
}

function downloadFile() {
  const a = document.createElement('a')
  a.href = `/api/doc/${props.fileId}/content?sa-token=${encodeURIComponent(getToken())}`
  a.download = props.fileName
  a.click()
}
</script>

<style scoped>
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 24px;
  font-weight: 300;
  letter-spacing: 0.05em;
}
.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 16px;
  overflow-x: auto;
  border: 1px solid #d4cdc5;
}
.markdown-body :deep(code) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #3d3d3d;
  padding-left: 16px;
  color: #666;
  margin: 16px 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #3d3d3d;
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(img) {
  max-width: 100%;
}
.docx-body {
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
}
</style>
