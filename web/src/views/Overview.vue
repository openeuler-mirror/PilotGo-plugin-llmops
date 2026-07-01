<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Plus } from '@element-plus/icons-vue'
import ProjectCard from '@/components/ProjectCard.vue'
import { listProjects, createProject, type Project as ApiProject } from '@/apis/project'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const { t } = useI18n()

const projects = ref<Array<{ id: number; name: string; description: string; status: string; lastUpdate: string; team: string }>>([])

const loadProjects = async () => {
  const list = await listProjects()
  projects.value = list.map((p: ApiProject) => ({
    id: p.id,
    name: p.name,
    description: p.desc ?? '',
    status: t('project.status.normal'),
    lastUpdate: p.updated_at || p.created_at || '-',
    team: t('project.team.unset')
  }))
}

// 处理查看项目详情
const handleViewProjectDetails = (projectId: number) => {
  console.log('查看项目详情:', projectId)
  // 导航到项目详情页，携带项目ID参数
  router.push(`/project/${projectId}`)
}

// 处理删除项目
const handleDeletedProject = async (projectId: number) => {
  await loadProjects()
}

onMounted(() => {
  loadProjects()
})

const createDialogVisible = ref(false)
const createLoading = ref(false)
const formRef = ref<FormInstance>()
const form = ref<{ name: string; desc: string }>({ name: '', desc: '' })
const rules: FormRules = {
  name: [{ required: true, message: t('project.form.namePlaceholder'), trigger: 'blur' }],
}
const openCreateDialog = () => {
  form.value = { name: '', desc: '' }
  createDialogVisible.value = true
}
const submitCreate = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  createLoading.value = true
  try {
    const msg = await createProject({ name: form.value.name, desc: form.value.desc })
    ElMessage.success(msg || t('overview.createSuccess'))
    createDialogVisible.value = false
    await loadProjects()
  } catch (e: any) {
    ElMessage.error(e?.message || t('overview.createFailed'))
  } finally {
    createLoading.value = false
  }
}
const cancelCreate = () => {
  createDialogVisible.value = false
}
</script>

<template>
  <div class="h-full bg-gray-50 flex flex-col">
    <!-- 页面标题 - 固定高度 -->
    <div class="flex justify-between items-center py-6 shrink-0">
      <div class="flex-1"></div>
      <div class="text-center">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">{{ $t('overview.title') }}</h1>
        <p class="text-gray-600">{{ $t('overview.subtitle') }}</p>
      </div>
      <div class="flex-1 flex justify-end">
        <el-button type="primary" size="large" class="mr-3" @click="openCreateDialog">
          <el-icon class="mr-2">
            <Plus />
          </el-icon>
          {{ $t('overview.createProject') }}
        </el-button>
      </div>
    </div>

    <!-- 项目卡片网格 - 可滚动区域 -->
    <div class="flex-1 overflow-y-auto" style="padding-right: 200px; padding-left: 200px;">
      <el-row :gutter="24">
        <el-col v-for="project in projects" :key="project.id" :xs="24" :sm="12" :md="8" :lg="6"
          style="padding-bottom: 20px;">
          <ProjectCard v-bind="project" @view-details="handleViewProjectDetails" @deleted="handleDeletedProject" />
        </el-col>
      </el-row>
    </div>
    <el-dialog v-model="createDialogVisible" :title="$t('overview.createProject')" width="500px" :lock-scroll="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="$t('project.form.name')" prop="name">
          <el-input v-model="form.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item :label="$t('project.form.desc')" prop="desc">
          <el-input v-model="form.desc" type="textarea" rows="4" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelCreate">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">{{ $t('overview.submitCreate') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
