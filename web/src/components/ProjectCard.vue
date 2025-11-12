<script setup lang="ts">
import { computed } from 'vue'

// 定义组件属性
interface Props {
  id: number
  name: string
  description: string
  status: string
  lastUpdate: string
  team: string
}

const props = defineProps<Props>()

// 获取状态样式
const statusStyle = computed(() => {
  switch (props.status) {
    case '正常':
      return { type: 'success' as const, text: 'success' }
    case '警告':
      return { type: 'warning' as const, text: 'warning' }
    case '错误':
      return { type: 'danger' as const, text: 'danger' }
    default:
      return { type: 'info' as const, text: 'info' }
  }
})

// 定义事件
const emit = defineEmits<{
  viewDetails: [id: number]
}>()

// 处理查看详情按钮点击
const handleViewDetails = () => {
  emit('viewDetails', props.id)
}
</script>

<template>
  <el-card :body-style="{ padding: '30px 20px', height: '350px', display: 'flex', flexDirection: 'column' }">
    <!-- 项目标题 -->
    <div class="mb-3">
      <h3 class="text-lg font-semibold text-gray-900 mb-1 line-clamp-1">
        {{ name }}
      </h3>
      <el-tag :type="statusStyle.type" size="small" class="mb-2">
        {{ status }}
      </el-tag>
    </div>

    <!-- 项目描述 -->
    <p class="text-gray-600 text-sm mb-4 line-clamp-3 flex-grow">
      {{ description }}
    </p>

    <!-- 项目信息 -->
    <div class="space-y-2">
      <div class="flex justify-between text-xs">
        <span class="text-gray-500">团队:</span>
        <span class="text-gray-700 font-medium">{{ team }}</span>
      </div>
      <div class="flex justify-between text-xs">
        <span class="text-gray-500">最后更新:</span>
        <span class="text-gray-700 font-medium">{{ lastUpdate }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="mt-4 pt-3 mt-2">
      <el-button type="primary" size="small" class="w-full" plain @click="handleViewDetails">
        查看详情
      </el-button>
    </div>
  </el-card>
</template>