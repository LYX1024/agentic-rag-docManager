import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as kbApi from '@/api/knowledgeBase'
import type { KnowledgeBase, CreateKBParams } from '@/api/knowledgeBase'

export const useKBStore = defineStore('knowledgeBase', () => {
  const kbList = ref<KnowledgeBase[]>([])
  const currentKB = ref<KnowledgeBase | null>(null)
  const loading = ref(false)

  async function fetchKBList(page: number = 1, size: number = 20) {
    loading.value = true
    try {
      const res = await kbApi.listKBs(page, size)
      kbList.value = res.data.records
    } finally {
      loading.value = false
    }
  }

  async function createKB(data: CreateKBParams) {
    const res = await kbApi.createKB(data)
    kbList.value.unshift(res.data)
    return res.data
  }

  async function deleteKB(id: number) {
    await kbApi.deleteKB(id)
    kbList.value = kbList.value.filter(kb => kb.id !== id)
  }

  function setCurrentKB(kb: KnowledgeBase | null) {
    currentKB.value = kb
  }

  return {
    kbList,
    currentKB,
    loading,
    fetchKBList,
    createKB,
    deleteKB,
    setCurrentKB
  }
})
