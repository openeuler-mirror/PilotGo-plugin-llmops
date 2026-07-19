<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { Odometer, Fold, Expand } from '@element-plus/icons-vue'

interface Notification {
  id: number
  message: string
  type: 'success' | 'info' | 'warning' | 'danger'
  timestamp: Date
}

// 模拟通知数据
const notifications = ref<Notification[]>([
  // {
  //   id: 1,
  //   message: '系统一切正常',
  //   type: 'success' as const,
  //   timestamp: new Date()
  // },
  // {
  //   id: 2,
  //   message: '系统一切正常',
  //   type: 'success' as const,
  //   timestamp: new Date()
  // },
])

// 关闭通知
const closeNotification = (id: number) => {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

// 侧边栏导航：根据当前路由高亮对应菜单项
const route = useRoute()
const activeMenu = computed(() => route.path)
const isCollapse = ref(false)

// 路由级面包屑导航
const breadcrumbs = computed(() => {
  const items: { text: string; to?: string }[] = [{ text: '总览', to: '/' }]
  if (route.path.startsWith('/project/')) {
    items.push({ text: '项目详情' })
  }
  return items
})
</script>

<template>
  <el-container class="h-screen overflow-hidden">
    <!-- 顶部标题栏 -->
    <el-header class="bg-white border-b border-gray-200 flex items-center shrink-0">
      <span class="text-lg font-semibold text-gray-800">PilotGo LLMOps</span>
      <el-breadcrumb separator="/" class="ml-6">
        <el-breadcrumb-item
          v-for="(item, idx) in breadcrumbs"
          :key="idx"
          :to="idx < breadcrumbs.length - 1 && item.to ? { path: item.to } : undefined"
        >
          {{ item.text }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </el-header>

    <el-container class="overflow-hidden">
      <!-- 左侧侧边栏导航 -->
      <el-aside :width="isCollapse ? '64px' : '200px'" class="bg-white border-r border-gray-200 flex flex-col transition-all duration-300">
        <!-- router 模式：菜单项 index 即路由路径，点击经 vue-router 跳转 -->
        <el-menu :default-active="activeMenu" router :collapse="isCollapse" :collapse-transition="false" class="flex-1 border-r-0">
          <el-menu-item index="/">
            <el-icon><Odometer /></el-icon>
            <template #title>
              <span>Overview</span>
            </template>
          </el-menu-item>
        </el-menu>
        <!-- 侧边栏折叠/展开按钮 -->
        <div class="h-10 flex items-center justify-center border-t border-gray-200 cursor-pointer hover:bg-gray-50" @click="isCollapse = !isCollapse">
          <el-icon>
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
      </el-aside>

      <!-- 右侧主区域：通知栏 + 路由页面 + footer -->
      <el-container class="flex flex-col overflow-hidden">
        <!-- 通知栏顶栏 -->
        <div class="shrink-0 space-y-2">
          <el-alert v-for="notification in notifications" :key="notification.id" :description="notification.message"
            :type="notification.type" show-icon :closable="true" @close="closeNotification(notification.id)" class="h-16" />
        </div>

        <!-- 主要内容区域 - 路由页面 -->
        <el-main class="flex-1 bg-gray-100 p-3! overflow-hidden">
          <!-- 路由页面占位 -->
          <RouterView />
        </el-main>

        <!-- Footer 区域 -->
        <el-footer class="bg-white shrink-0" style="height: 50px;">
          <div class="h-full flex items-center justify-center">
            <p class="text-sm text-gray-500">
              &copy; KylinSoft 2026, All rights reserved | PilotGo-plugin-llmops v0.0.0
            </p>
          </div>
        </el-footer>
      </el-container>
    </el-container>
  </el-container>
</template>
