<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'

interface AuditItem {
  id: number | string
  time: string
  operator: string
  component: string
  description: string
}

const props = defineProps<{ projectId: string | number }>()

const logs = ref<AuditItem[]>([])
const currentPage = ref(1)
const totalPages = ref(1)

const loadLogs = async () => {
  try {
    const res = await fetch(`/api/projects/${props.projectId}/audit/logs?page=${currentPage.value}`)
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) {
        logs.value = data as AuditItem[]
        totalPages.value = 1
      } else if (data && Array.isArray(data.items)) {
        logs.value = data.items as AuditItem[]
        totalPages.value = Number((data.totalPages ?? data.total_pages) || 1)
      } else {
        logs.value = []
        totalPages.value = 1
      }
    }
  } catch (e) {}
}

onMounted(() => {
  loadLogs()
})

watch(
  () => props.projectId,
  () => {
    currentPage.value = 1
    loadLogs()
  }
)

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadLogs()
}
</script>

<template>
  <div class="h-full flex flex-col">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">审计日志</h2>
    <MTable :data="logs" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange" class="flex-1">
      <template #columns>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="operator" label="操作人" width="140" />
        <el-table-column prop="component" label="操作组件" min-width="180" show-overflow-tooltip />
        <el-table-column prop="description" label="变更描述" min-width="300" show-overflow-tooltip />
      </template>
    </MTable>
  </div>
</template>