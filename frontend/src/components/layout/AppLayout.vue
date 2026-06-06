<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#F9F6F3]">
    <aside class="w-[260px] bg-[#f5f0eb] border-r border-[#d4cdc5]/40 flex flex-col flex-shrink-0">
      <slot name="sidebar">
        <NavLinks :current="currentHighlight" @docbase="goDocBase" />
        <div class="flex-1" />
        <div class="p-4 border-t border-[#d4cdc5]/40 flex items-center justify-between">
          <span class="font-light text-sm text-[#3d3d3d]/60 truncate">{{ username }}</span>
          <button
            class="font-light text-xs text-[#3d3d3d]/40 hover:text-[#607683] transition-colors duration-700 ease-in-out cursor-pointer"
            @click="handleLogout"
          >退出</button>
        </div>
      </slot>
    </aside>
    <main class="flex-1 overflow-y-auto bg-[#F9F6F3]">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useKBStore } from '@/stores/knowledgeBase'
import { Toast } from '@/utils/toast'
import NavLinks from './NavLinks.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const kbStore = useKBStore()
const username = computed(() => authStore.user?.username || '')

const currentHighlight = computed(() => {
  if (route.path === '/dashboard') return '/dashboard'
  if (route.path.startsWith('/kb/') || route.path.startsWith('/search/')) return '/docbase'
  if (route.path.startsWith('/chat')) return '/chat'
  return null
})

async function goDocBase() {
  await kbStore.fetchKBList()
  if (kbStore.kbList.length > 0) router.push(`/kb/${kbStore.kbList[0].id}`)
  else Toast.warning('请先创建知识库')
}

function handleLogout() { authStore.logout() }
</script>
