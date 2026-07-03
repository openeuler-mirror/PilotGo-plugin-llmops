<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'
import { listProjectAuditLogs, listAuditByFilters, type AuditItem } from '@/apis/audit'

const props = defineProps<{ projectId: string | number }>()

const logs = ref<AuditItem[]>([])
const currentPage = ref(1)
const totalPages = ref(1)

const filterActor = ref('')
const filterActionType = ref('')
const filterTarget = ref('')

const loadLogs = async () => {
  try {
    const hasFilter = !!(filterActor.value || filterActionType.value || filterTarget.value)
    const res = hasFilter
      ? await listAuditByFilters(
          props.projectId,
          { actor: filterActor.value, actionType: filterActionType.value, target: filterTarget.value },
          currentPage.value,
        )
      : await listProjectAuditLogs(props.projectId, currentPage.value)
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
    filterActor.value = ''
    filterActionType.value = ''
    filterTarget.value = ''
    loadLogs()
  }
)

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadLogs()
}

const handleSearch = () => {
  currentPage.value = 1
  loadLogs()
}

const handleReset = () => {
  filterActor.value = ''
  filterActionType.value = ''
  filterTarget.value = ''
  currentPage.value = 1
  loadLogs()
}
</script>

<template>
  <div class="h-full flex flex-col">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">{{ $t('audit.title') }}</h2>
    <div class="flex gap-2 mb-4">
      <el-input v-model="filterActor" :placeholder="$t('audit.filter.actor')" clearable class="!w-40" />
      <el-input v-model="filterActionType" :placeholder="$t('audit.filter.actionType')" clearable class="!w-40" />
      <el-input v-model="filterTarget" :placeholder="$t('audit.filter.target')" clearable class="!w-40" />
      <el-button type="primary" @click="handleSearch">{{ $t('audit.filter.search') }}</el-button>
      <el-button @click="handleReset">{{ $t('audit.filter.reset') }}</el-button>
    </div>
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
