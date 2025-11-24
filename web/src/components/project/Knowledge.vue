<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import MTable from '../common/MTable.vue'
import { uploadKnowledge, listKnowledgeFiles } from '../../apis/knowledge'

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
const uploadVisible = ref(false)
const uploading = ref(false)
const selectedFile = ref<File | null>(null)
const objectName = ref('')
const uploader = ref('')
const description = ref('')

const loadFiles = async () => {
  loading.value = true
  try {
    const data = await listKnowledgeFiles(props.projectId, currentPage.value)
    if (Array.isArray(data)) {
      files.value = data as KnowledgeFile[]
      totalPages.value = 1
    } else if (data && Array.isArray(data.items)) {
      files.value = data.items as KnowledgeFile[]
      totalPages.value = Number((data as any).totalPages || (data as any).total_pages || 1)
    } else {
      files.value = []
      totalPages.value = 1
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

const openUpload = () => {
  uploadVisible.value = true
}

const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files && target.files[0]
  selectedFile.value = file || null
  if (file && !objectName.value) {
    objectName.value = file.name
  }
}

const doUpload = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    await uploadKnowledge({
      projectId: Number(props.projectId),
      file: selectedFile.value,
      object: objectName.value || undefined,
      uploader: uploader.value || undefined,
      desc: description.value || undefined,
    })
    uploadVisible.value = false
    selectedFile.value = null
    objectName.value = ''
    uploader.value = ''
    description.value = ''
    loadFiles()
  } catch (e) {
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">集群知识库</h2>
      <el-button type="primary" @click="openUpload">上传文件</el-button>
    </div>
    <MTable :data="files" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange"
      class="flex-1">
      <template #columns>
        <el-table-column prop="filename" label="文件名" min-width="220" />
        <el-table-column prop="fileType" label="文件类型" min-width="80" />
        <el-table-column prop="uploadedAt" label="上传时间" width="180" />
        <el-table-column prop="uploader" label="上传人" width="140" />
        <el-table-column prop="description" label="文件描述" min-width="300" show-overflow-tooltip />
      </template>
    </MTable>
    <el-dialog v-model="uploadVisible" title="上传文件" width="520px">
      <div class="space-y-4">
        <div class="flex items-center">
          <span class="w-20 text-gray-600">文件</span>
          <input type="file" @change="onFileSelect" />
        </div>
        <div class="flex items-center">
          <span class="w-20 text-gray-600">对象名</span>
          <el-input v-model="objectName" placeholder="默认使用文件名" />
        </div>
        <div class="flex items-center">
          <span class="w-20 text-gray-600">上传人</span>
          <el-input v-model="uploader" />
        </div>
        <div class="flex items-start">
          <span class="w-20 text-gray-600 leading-8">描述</span>
          <el-input type="textarea" v-model="description" />
        </div>
      </div>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>
