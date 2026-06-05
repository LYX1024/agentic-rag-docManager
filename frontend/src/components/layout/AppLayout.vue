<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="app-aside">
      <AppSidebar />
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <AppHeader />
      </el-header>
      <el-main class="app-main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
</script>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;

  .app-aside {
    background-color: #001529;
    overflow: hidden;
  }

  .app-header {
    background: #fff;
    border-bottom: 1px solid #e8e8e8;
    padding: 0 24px;
    display: flex;
    align-items: center;
    height: 56px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  }

  .app-main {
    background-color: #f5f7fa;
    padding: 24px;
    overflow-y: auto;
    height: calc(100vh - 56px);
  }
}
</style>
