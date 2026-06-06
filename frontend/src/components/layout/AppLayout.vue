<template>
  <div class="flex flex-col h-screen w-screen overflow-hidden bg-[#f5f0eb]">
    <!-- Top Navbar -->
    <header class="h-14 bg-[#f5f0eb] border-b border-[#d4cdc5]/40 flex items-center justify-center px-6 flex-shrink-0 relative">
      <nav class="flex items-center gap-8">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="font-light text-sm tracking-wide transition-colors duration-700 ease-in-out"
          :class="isActive(item.path) ? 'text-[#5a7a6b]' : 'text-[#3d3d3d]/60 hover:text-[#3d3d3d]'"
        >
          {{ item.label }}
        </router-link>
      </nav>
      <div class="absolute right-6 flex items-center gap-4">
        <span class="font-light text-sm text-[#3d3d3d]/60">{{ username }}</span>
        <button
          class="font-light text-sm text-[#3d3d3d]/60 hover:text-[#607683] transition-colors duration-700 ease-in-out cursor-pointer"
          @click="handleLogout"
        >
          退出
        </button>
      </div>
    </header>

    <!-- Content -->
    <main class="flex-1 overflow-y-auto">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || '')

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/chat', label: 'Chat' }
]

function isActive(path: string): boolean {
  if (path === '/dashboard' && (route.path.startsWith('/dashboard') || route.path.startsWith('/kb') || route.path.startsWith('/search'))) {
    return true
  }
  if (path === '/chat' && route.path.startsWith('/chat')) {
    return true
  }
  return false
}

function handleLogout() {
  authStore.logout()
}
</script>
