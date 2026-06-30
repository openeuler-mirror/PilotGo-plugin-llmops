<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import MTable from '../common/MTable.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadKnowledge, listKnowledgeFiles, deleteKnowledge as deleteKnowledgeApi, type KnowledgeFile } from '../../apis/knowledge'

const props = defineProps<{ projectId: string }>()
const { t } = useI18n()

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
    files.value = Array.isArray(data) ? data : []
    totalPages.value = 1
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

const deleteKnowledge = async (row: any) => {
  try {
    await ElMessageBox.confirm(t('knowledge.deleteConfirm'), t('knowledge.deleteConfirmTitle'), { type: 'warning', confirmButtonText: t('common.delete'), cancelButtonText: t('common.cancel'), lockScroll: false })
    const id = Number(row?.id)
    if (!id || isNaN(id)) {
      ElMessage.error(t('knowledge.deleteMissingId'))
      return
    }
    const msg = await deleteKnowledgeApi(id)
    ElMessage.success(msg || t('knowledge.deleteSuccess'))
    loadFiles()
  } catch (e) {}
}
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">{{ $t('knowledge.title') }}</h2>
      <el-button type="primary" @click="openUpload">{{ $t('knowledge.upload') }}</el-button>
    </div>
    <MTable :data="files" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange"
      class="flex-1">
      <template #columns>
        <el-table-column prop="filename" :label="$t('knowledge.columns.filename')" min-width="220" />
        <el-table-column prop="fileType" :label="$t('knowledge.columns.fileType')" min-width="80" />
        <el-table-column prop="uploadedAt" :label="$t('knowledge.columns.uploadedAt')" width="180" />
        <el-table-column prop="uploader" :label="$t('knowledge.columns.uploader')" width="140" />
        <el-table-column prop="description" :label="$t('knowledge.columns.description')" min-width="300" show-overflow-tooltip />
        <el-table-column :label="$t('knowledge.columns.action')" width="80">
          <template #default="scope">
            <el-button type="danger" size="mini" @click="deleteKnowledge(scope.row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </template>
    </MTable>
    <el-dialog v-model="uploadVisible" :title="$t('knowledge.upload')" width="520px">
      <div class="space-y-4">
        <div class="flex items-center">
          <span class="w-20 text-gray-600">{{ $t('knowledge.form.file') }}</span>
          <input type="file" @change="onFileSelect" />
        </div>
        <div class="flex items-center">
          <span class="w-20 text-gray-600">{{ $t('knowledge.form.object') }}</span>
          <el-input v-model="objectName" :placeholder="$t('knowledge.form.objectPlaceholder')" />
        </div>
        <div class="flex items-center">
          <span class="w-20 text-gray-600">{{ $t('knowledge.form.uploader') }}</span>
          <el-input v-model="uploader" />
        </div>
        <div class="flex items-start">
          <span class="w-20 text-gray-600 leading-8">{{ $t('knowledge.form.desc') }}</span>
          <el-input type="textarea" v-model="description" />
        </div>
      </div>
      <template #footer>
        <el-button @click="uploadVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="doUpload">{{ $t('knowledge.submitUpload') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
