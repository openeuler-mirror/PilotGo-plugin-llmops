<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'
import { listProjectAuditLogs, type AuditItem } from '@/apis/audit'

const props = defineProps<{ projectId: string | number }>()

const logs = ref<AuditItem[]>([])
const currentPage = ref(1)
const totalPages = ref(1)

const loadLogs = async () => {
  try {
    const res = await listProjectAuditLogs(props.projectId, currentPage.value)
    logs.value = res.data
    totalPages.value = Math.max(1, Math.ceil(res.total / (res.perpage || 20)))
  } catch {}
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
    <h2 class="text-xl font-semibold text-gray-800 mb-4">{{ $t('audit.title') }}</h2>
    <MTable :data="logs" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange" class="flex-1">
      <template #columns>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="time" :label="$t('audit.columns.time')" width="180" />
        <el-table-column prop="operator" :label="$t('audit.columns.operator')" width="140" />
        <el-table-column prop="component" :label="$t('audit.columns.component')" min-width="180" show-overflow-tooltip />
        <el-table-column prop="description" :label="$t('audit.columns.description')" min-width="300" show-overflow-tooltip />
      </template>
    </MTable>
  </div>
</template>
