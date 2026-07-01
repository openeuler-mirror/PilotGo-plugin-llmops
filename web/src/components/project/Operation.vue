<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import MTable from '../common/MTable.vue'
import { listOperationScripts, createOperationScript, updateOperationScript, type OperationScript } from '../../apis/operation'

interface ScriptItem {
  id: number | string
  name: string
  description: string
  updatedBy: string
  updatedAt: string
}

const { t } = useI18n()

const props = defineProps<{ projectId: string | number }>()

const scripts = ref<OperationScript[]>([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)

const emit = defineEmits<{
  (e: 'run', id: number | string): void
  (e: 'delete', id: number | string): void
}>()

// 新建/编辑脚本弹窗(组件自持:projectId 来自 props,提交后本地 loadScripts 刷新)
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | string>('')
const formRef = ref<FormInstance>()
const form = ref<{ name: string; description: string; content: string; updatedBy: string }>({
  name: '',
  description: '',
  content: '',
  updatedBy: '',
})
const formRules = computed<FormRules>(() => ({
  name: [{ required: true, message: t('operationView.rules.nameRequired'), trigger: 'blur' }],
}))

const openCreateDialog = () => {
  dialogMode.value = 'create'
  editingId.value = ''
  form.value = { name: '', description: '', content: '', updatedBy: '' }
  dialogVisible.value = true
}

const openEditDialog = (row: OperationScript) => {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.value = {
    name: row.name ?? '',
    description: row.description ?? '',
    content: row.content ?? '',
    updatedBy: row.updatedBy ?? '',
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  dialogLoading.value = true
  try {
    if (dialogMode.value === 'create') {
      const msg = await createOperationScript(props.projectId, form.value)
      ElMessage.success(msg || t('operationView.createSuccess'))
    } else {
      const msg = await updateOperationScript(props.projectId, editingId.value, form.value)
      ElMessage.success(msg || t('operationView.updateSuccess'))
    }
    dialogVisible.value = false
    loadScripts()
  } catch {
    // 失败提示由 request.ts 的 handleError 统一弹出,此处仅吞掉 rejection
  } finally {
    dialogLoading.value = false
  }
}

const loadScripts = async () => {
  loading.value = true
  try {
    scripts.value = await listOperationScripts(props.projectId, currentPage.value)
    totalPages.value = 1
  } catch (e) {
    console.error('加载运维脚本失败', e)
    scripts.value = []
    totalPages.value = 1
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

const handleRun = (row: ScriptItem) => emit('run', row.id)
const handleDelete = (row: ScriptItem) => {
  ElMessageBox.confirm(t('operationView.deleteConfirm', { name: row.name }), t('operationView.deleteConfirmTitle'), {
    type: 'warning',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
  })
    .then(() => emit('delete', row.id))
    .catch(() => {})
}

defineExpose({ loadScripts })
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-semibold text-gray-800">{{ $t('operationView.title') }}</h2>
      <el-button type="primary" @click="openCreateDialog">{{ $t('operationView.create') }}</el-button>
    </div>
    <MTable :data="scripts" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange" class="flex-1">
      <template #columns>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="name" :label="$t('operationView.columns.name')" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" :label="$t('operationView.columns.description')" min-width="300" show-overflow-tooltip />
        <el-table-column prop="updatedBy" :label="$t('operationView.columns.updatedBy')" width="140" />
        <el-table-column prop="updatedAt" :label="$t('operationView.columns.updatedAt')" width="180" />
        <el-table-column :label="$t('operationView.columns.action')" width="240">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">{{ $t('common.edit') }}</el-button>
            <el-button type="success" size="small" class="ml-2" @click="handleRun(row)">{{ $t('operationView.run') }}</el-button>
            <el-button type="danger" size="small" class="ml-2" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </template>
    </MTable>

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? $t('operationView.dialog.createTitle') : $t('operationView.dialog.editTitle')" width="600px" :lock-scroll="false">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item :label="$t('operationView.form.name')" prop="name">
          <el-input v-model="form.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item :label="$t('operationView.form.description')" prop="description">
          <el-input v-model="form.description" type="textarea" rows="2" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item :label="$t('operationView.form.content')" prop="content">
          <el-input v-model="form.content" type="textarea" rows="6" />
        </el-form-item>
        <el-form-item :label="$t('operationView.form.updatedBy')" prop="updatedBy">
          <el-input v-model="form.updatedBy" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submitForm">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>