<script setup lang="ts">
import { ref } from 'vue'
import { RouterView } from 'vue-router'

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

</script>

<template>
  <el-container class="h-screen flex flex-col overflow-hidden">
    <!-- 通知栏顶栏 -->
    <div class="flex-shrink-0 space-y-2">
      <el-alert v-for="notification in notifications" :key="notification.id" :description="notification.message"
        :type="notification.type" show-icon :closable="true" @close="closeNotification(notification.id)" class="h-16" />
    </div>

    <!-- 主要内容区域 - 路由页面 -->
    <el-main class="flex-1 bg-gray-100 p-0 overflow-hidden">
      <!-- 路由页面占位 -->
      <RouterView />
    </el-main>

    <!-- Footer 区域 -->
    <el-footer class="bg-white flex-shrink-0" style="height: 50px;">
      <div class="h-full flex items-center justify-center">
        <p class="text-sm text-gray-500">
          &copy; KylinSoft 2024, All rights reserved | PilotGo-plugin-llmops v0.0.0
        </p>
      </div>
    </el-footer>
  </el-container>
</template>
