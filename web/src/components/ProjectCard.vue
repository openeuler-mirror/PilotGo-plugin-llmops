<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteProject } from '@/apis/project'
import StatusTag from '@/components/common/StatusTag.vue'

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

// 定义事件
const emit = defineEmits<{
  viewDetails: [id: number]
  deleted: [id: number]
}>()

// 处理查看详情按钮点击
const handleViewDetails = () => {
  emit('viewDetails', props.id)
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确认删除该项目？', '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', lockScroll: false })
    await ElMessageBox.confirm('该操作不可恢复，是否继续？', '再次确认', { type: 'error', confirmButtonText: '继续删除', cancelButtonText: '取消', lockScroll: false })
    const msg = await deleteProject(props.id)
    ElMessage.success(msg || '删除成功')
    emit('deleted', props.id)
  } catch {}
}
</script>

<template>
  <el-card :body-style="{ padding: '20px 20px', height: '350px', display: 'flex', flexDirection: 'column' }">
    <!-- 项目标题 -->
    <div class="mb-3">
      <h3 class="text-lg font-semibold text-gray-900 mb-1 line-clamp-1">
        {{ name }}
      </h3>
      <StatusTag :status="status" size="small" class="mb-2" />
    </div>

    <!-- 项目描述 -->
    <p class="text-gray-600 text-sm mb-4 line-clamp-3 grow">
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
    <div class="pt-3 mt-2 flex">
      <el-button type="primary" size="middle" class="w-full" plain @click="handleViewDetails">
        查看详情
      </el-button>
      <el-button type="danger" size="middle" class="w-16" plain @click="handleDelete">
        删除
      </el-button>
    </div>
  </el-card>
</template>