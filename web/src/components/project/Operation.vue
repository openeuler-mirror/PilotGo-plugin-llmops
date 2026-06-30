<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
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
const formRules: FormRules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
}

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
      ElMessage.success(msg || '创建成功')
    } else {
      const msg = await updateOperationScript(props.projectId, editingId.value, form.value)
      ElMessage.success(msg || '更新成功')
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
  ElMessageBox.confirm(`确定删除脚本「${row.name}」吗?`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
    .then(() => emit('delete', row.id))
    .catch(() => {})
}

defineExpose({ loadScripts })
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-semibold text-gray-800">集群运维脚本</h2>
      <el-button type="primary" @click="openCreateDialog">新建</el-button>
    </div>
    <MTable :data="scripts" :currentPage="currentPage" :totalPages="totalPages" @page-change="handlePageChange" class="flex-1">
      <template #columns>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="name" label="名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="updatedBy" label="更新人" width="140" />
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button type="success" size="small" class="ml-2" @click="handleRun(row)">运行</el-button>
            <el-button type="danger" size="small" class="ml-2" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </template>
    </MTable>

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新建脚本' : '编辑脚本'" width="600px" :lock-scroll="false">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="2" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" rows="6" />
        </el-form-item>
        <el-form-item label="更新人" prop="updatedBy">
          <el-input v-model="form.updatedBy" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>