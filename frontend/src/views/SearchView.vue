<template>
  <AppLayout>
    <div class="search-page">
      <div class="search-header">
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <h1>知识库检索</h1>
      </div>

      <div class="search-panel">
        <SearchBar
          v-model:query="query"
          v-model:search-mode="searchMode"
          :loading="searching"
          @search="executeSearch"
        />
      </div>

      <div class="search-options">
        <div class="option-item">
          <span class="option-label">相似度阈值: {{ scoreThreshold.toFixed(2) }}</span>
          <el-slider
            v-model="scoreThreshold"
            :min="0"
            :max="1"
            :step="0.05"
            style="width: 200px"
            :show-tooltip="false"
          />
        </div>
        <div class="option-item">
          <span class="option-label">返回条数</span>
          <el-select v-model="topK" style="width: 100px">
            <el-option :value="5" label="5" />
            <el-option :value="10" label="10" />
            <el-option :value="20" label="20" />
            <el-option :value="50" label="50" />
          </el-select>
        </div>
      </div>

      <div v-if="searching" class="loading-area">
        <el-skeleton :rows="4" animated />
      </div>

      <div v-else-if="searchPerformed && results.length === 0" class="empty-area">
        <el-empty description="未找到相关结果" />
      </div>

      <div v-else-if="results.length > 0" class="results-area">
        <div class="results-info">
          <span>找到 {{ total }} 条结果</span>
          <el-tag v-if="timeCost !== undefined" size="small" type="info">
            耗时 {{ timeCost }}ms
          </el-tag>
        </div>
        <SearchResult
          v-for="(result, idx) in results"
          :key="idx"
          :result="result"
          :query="highlightQuery"
        />
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import SearchBar from '@/components/search/SearchBar.vue'
import SearchResult from '@/components/search/SearchResult.vue'
import * as searchApi from '@/api/search'
import type { SearchResultItem } from '@/api/search'

const route = useRoute()
const router = useRouter()

const kbId = Number(route.params.kbId)

const query = ref('')
const searchMode = ref<string>('hybrid')
const scoreThreshold = ref(0.35)
const topK = ref(10)

const searching = ref(false)
const searchPerformed = ref(false)
const results = ref<SearchResultItem[]>([])
const total = ref(0)
const timeCost = ref<number | undefined>()
const highlightQuery = ref('')

onMounted(() => {
  const q = route.query.q as string
  if (q) {
    query.value = q
    executeSearch()
  }
})

function goBack() {
  router.push(`/kb/${kbId}`)
}

async function executeSearch() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }

  searching.value = true
  searchPerformed.value = true
  highlightQuery.value = query.value

  try {
    let res
    if (searchMode.value === 'hybrid') {
      res = await searchApi.hybridSearch({
        query: query.value,
        kbId,
        topK: topK.value,
        scoreThreshold: scoreThreshold.value,
        alpha: 0.3,
        beta: 0.7
      })
    } else if (searchMode.value === 'vector') {
      res = await searchApi.search({
        query: query.value,
        kbId,
        topK: topK.value,
        scoreThreshold: scoreThreshold.value,
        searchMode: 'vector'
      })
    } else {
      res = await searchApi.search({
        query: query.value,
        kbId,
        topK: topK.value,
        scoreThreshold: scoreThreshold.value,
        searchMode: 'bm25'
      })
    }

    results.value = res.data.results
    total.value = res.data.total
    timeCost.value = res.data.timeCost
  } catch {
    ElMessage.error('搜索失败，请稍后重试')
    results.value = []
    total.value = 0
  } finally {
    searching.value = false
  }
}
</script>

<style scoped lang="scss">
.search-page {
  max-width: 900px;
  margin: 0 auto;

  .search-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;

    h1 {
      font-size: 22px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }

  .search-panel {
    margin-bottom: 16px;
  }

  .search-options {
    display: flex;
    align-items: center;
    gap: 32px;
    padding: 12px 16px;
    background: #fff;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid #ebeef5;

    .option-item {
      display: flex;
      align-items: center;
      gap: 12px;

      .option-label {
        font-size: 13px;
        color: #606266;
        white-space: nowrap;
      }
    }
  }

  .loading-area {
    padding: 20px;
    background: #fff;
    border-radius: 8px;
  }

  .empty-area {
    margin-top: 40px;
  }

  .results-area {
    .results-info {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      font-size: 13px;
      color: #909399;
    }
  }
}
</style>
