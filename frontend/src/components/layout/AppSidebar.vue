<template>
  <div class="sidebar-container">
    <div class="sidebar-logo">
      <el-icon :size="24"><Reading /></el-icon>
      <span class="logo-text">知识库平台</span>
    </div>
    <el-menu
      :default-active="activeMenu"
      :router="true"
      background-color="#001529"
      text-color="#ffffffa6"
      active-text-color="#409eff"
      class="sidebar-menu"
    >
      <el-menu-item index="/dashboard">
        <el-icon><DataBoard /></el-icon>
        <span>仪表盘</span>
      </el-menu-item>
      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>智能对话</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataBoard, ChatDotRound, Reading } from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/dashboard') || path.startsWith('/kb')) {
    return '/dashboard'
  }
  if (path.startsWith('/chat')) {
    return '/chat'
  }
  return path
})
</script>

<style scoped lang="scss">
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;

  .sidebar-logo {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .logo-text {
      font-size: 16px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  .sidebar-menu {
    flex: 1;
    border-right: none;
    overflow-y: auto;
  }
}
</style>
