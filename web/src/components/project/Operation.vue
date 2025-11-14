<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'

interface ScriptItem {
  id: number | string
  name: string
  description: string
  updatedBy: string
  updatedAt: string
}

const props = defineProps<{ projectId: string | number }>()

const scripts = ref<ScriptItem[]>([
    {
        id: 1,
        name: '扩充Nginx实例',
        description: '扩充n个Nginx实例，提升集群服务能力',
        updatedBy: 'admin',
        updatedAt: '2023-01-01 00:00:00',
    },
])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)

const emit = defineEmits<{
  (e: 'edit', id: number | string): void
  (e: 'run', id: number | string): void
  (e: 'delete', id: number | string): void
}>()

const loadScripts = async () => {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/operation/scripts?page=${currentPage.value}`)
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) {
        scripts.value = data as ScriptItem[]
        totalPages.value = 1
      } else if (data && Array.isArray(data.items)) {
        scripts.value = data.items as ScriptItem[]
        totalPages.value = Number((data.totalPages ?? data.total_pages) || 1)
      } else {
        scripts.value = []
        totalPages.value = 1
      }
    }
  } catch (e) {
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadScripts()
})

watch(
  () => props.projectId,
  () => {
    currentPage.value = 1
    loadScripts()
  }
)

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadScripts()
}

const handleEdit = (row: ScriptItem) => emit('edit', row.id)
const handleRun = (row: ScriptItem) => emit('run', row.id)
const handleDelete = (row: ScriptItem) => emit('delete', row.id)
</script>

<template>
  <div class="h-full flex flex-col">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">集群运维脚本</h2>
    <MTable :data="scripts" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange" class="flex-1">
      <template #columns>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="name" label="名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="updatedBy" label="更新人" width="140" />
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="success" size="small" class="ml-2" @click="handleRun(row)">运行</el-button>
            <el-button type="danger" size="small" class="ml-2" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </template>
    </MTable>
  </div>
</template>