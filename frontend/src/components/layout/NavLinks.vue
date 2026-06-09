<template>
  <nav class="p-4 flex flex-col gap-0.5">
    <router-link
      to="/dashboard"
      class="block px-3 py-2 font-light text-sm transition-all duration-700 ease-in-out"
      :style="current === '/dashboard'
        ? { color: '#3d3d3d', borderBottom: '2px solid #3d3d3d' }
        : { color: '#a89279', borderBottom: '2px solid transparent' }"
      @mouseenter="(e) => { if (current !== '/dashboard') (e.target as HTMLElement).style.color = '#3d3d3d' }"
      @mouseleave="(e) => { if (current !== '/dashboard') (e.target as HTMLElement).style.color = '#a89279' }"
    >Dashboard</router-link>
    <a
      class="block px-3 py-2 font-light text-sm transition-all duration-700 ease-in-out cursor-pointer"
      :style="current === '/docbase'
        ? { color: '#3d3d3d', borderBottom: '2px solid #3d3d3d' }
        : { color: '#a89279', borderBottom: '2px solid transparent' }"
      @mouseenter="(e) => { if (current !== '/docbase') (e.target as HTMLElement).style.color = '#3d3d3d' }"
      @mouseleave="(e) => { if (current !== '/docbase') (e.target as HTMLElement).style.color = '#a89279' }"
      @click="$emit('docbase')"
    >DocBase</a>
    <router-link
      to="/chat"
      class="block px-3 py-2 font-light text-sm transition-all duration-700 ease-in-out"
      :style="current === '/chat'
        ? { color: '#3d3d3d', borderBottom: '2px solid #3d3d3d' }
        : { color: '#a89279', borderBottom: '2px solid transparent' }"
      @mouseenter="(e) => { if (current !== '/chat') (e.target as HTMLElement).style.color = '#3d3d3d' }"
      @mouseleave="(e) => { if (current !== '/chat') (e.target as HTMLElement).style.color = '#a89279' }"
    >Chat</router-link>
  </nav>
</template>

<script setup lang="ts">
defineProps<{ current: string | null }>()
defineEmits<{ (e: 'docbase'): void }>()
</script>
