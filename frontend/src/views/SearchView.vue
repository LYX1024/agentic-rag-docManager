<template>
  <AppLayout>
    <div class="px-6 md:px-12 py-8 max-w-[900px] mx-auto">
      <!-- Header -->
      <div class="flex items-center gap-4 mb-6">
        <AppButton variant="secondary" size="sm" @click="goBack">
          ← 返回
        </AppButton>
        <h1 class="font-light tracking-wide text-2xl">知识库检索</h1>
      </div>

      <!-- Search Panel -->
      <div class="mb-4">
        <SearchBar
          :query="query"
          :search-mode="searchMode"
          :loading="searching"
          @update:query="query = $event"
          @update:search-mode="searchMode = $event"
          @search="executeSearch"
        />
      </div>

      <!-- Search Options -->
      <div class="flex items-center gap-8 p-3 bg-white border border-[#d4cdc5]/40 mb-5">
        <div class="flex items-center gap-3">
          <span class="font-light text-xs text-[#3d3d3d] whitespace-nowrap">
            相似度阈值: {{ scoreThreshold.toFixed(2) }}
          </span>
          <input
            v-model.number="scoreThreshold"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="w-[150px] accent-[#5a7a6b]"
          />
        </div>
        <div class="flex items-center gap-3">
          <span class="font-light text-xs text-[#3d3d3d] whitespace-nowrap">返回条数</span>
          <select
            v-model.number="topK"
            class="bg-white border border-[#d4cdc5]/40 px-2 py-1 font-light text-xs focus:outline-none"
          >
            <option :value="5">5</option>
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="searching" class="p-5 bg-white border border-[#d4cdc5]/40">
        <p class="font-light text-sm text-gray-500">搜索中...</p>
      </div>

      <!-- Empty -->
      <div v-else-if="searchPerformed && results.length === 0" class="flex flex-col items-center justify-center py-20">
        <p class="font-light tracking-wide text-lg text-gray-500">未找到相关结果</p>
      </div>

      <!-- Results -->
      <div v-else-if="results.length > 0">
        <div class="flex items-center gap-3 mb-3">
          <span class="font-light text-xs text-gray-500">找到 {{ total }} 条结果</span>
          <span v-if="timeCost !== undefined" class="font-light text-xs px-2 py-0.5 border border-[#d4cdc5]/40 bg-white">
            耗时 {{ timeCost }}ms
          </span>
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
import { Toast } from '@/utils/toast'
import AppLayout from '@/components/layout/AppLayout.vue'
import AppButton from '@/components/ui/AppButton.vue'
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
    Toast.warning('请输入搜索内容')
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
    Toast.error('搜索失败，请稍后重试')
    results.value = []
    total.value = 0
  } finally {
    searching.value = false
  }
}
</script>
