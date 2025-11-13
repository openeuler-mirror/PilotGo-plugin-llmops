<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'

interface KnowledgeFile {
  filename: string
  fileType: string
  uploadedAt: string
  uploader: string
  description: string
}

const props = defineProps<{ projectId: string }>()

const files = ref<KnowledgeFile[]>([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)

const loadFiles = async () => {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/knowledge/files?page=${currentPage.value}`)
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) {
        files.value = data as KnowledgeFile[]
        totalPages.value = 1
      } else if (data && Array.isArray(data.items)) {
        files.value = data.items as KnowledgeFile[]
        totalPages.value = Number(data.totalPages || data.total_pages || 1)
      } else {
        files.value = []
        totalPages.value = 1
      }
    }
  } catch (e) {
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadFiles()
})

watch(
  () => props.projectId,
  () => {
    currentPage.value = 1
    loadFiles()
  }
)

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadFiles()
}
</script>

<template>
  <div class="h-full">
    <MTable :data="files" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange">
      <template #columns>
        <el-table-column prop="filename" label="文件名" min-width="220" />
        <el-table-column prop="fileType" label="文件类型" min-width="80" />
        <el-table-column prop="uploadedAt" label="上传时间" width="180" />
        <el-table-column prop="uploader" label="上传人" width="140" />
        <el-table-column prop="description" label="文件描述" min-width="300" show-overflow-tooltip />
      </template>
    </MTable>
  </div>
</template>