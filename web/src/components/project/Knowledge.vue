<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

interface KnowledgeFile {
  filename: string
  uploadedAt: string
  uploader: string
  description: string
}

const props = defineProps<{ projectId: string }>()

const files = ref<KnowledgeFile[]>([])
const loading = ref(false)

const loadFiles = async () => {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/knowledge/files`)
    if (res.ok) {
      const data = await res.json()
      files.value = Array.isArray(data) ? (data as KnowledgeFile[]) : []
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
    loadFiles()
  }
)
</script>

<template>
  <div class="h-full">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">项目知识库清单</h2>
    <el-table :data="files" border stripe class="w-full">
      <el-table-column prop="filename" label="文件名" min-width="220" />
      <el-table-column prop="fileType" label="文件类型" min-width="80" />
      <el-table-column prop="uploadedAt" label="上传时间" width="180" />
      <el-table-column prop="uploader" label="上传人" width="140" />
      <el-table-column prop="description" label="文件描述" min-width="300" show-overflow-tooltip />
    </el-table>
  </div>
</template>