<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Checked,
  Share,
  Warning,
  Monitor,
  ArrowLeft,
  DocumentCopy,
  Operation
} from '@element-plus/icons-vue'
import Topology from '../components/project/Topology.vue'
import Knowledge from '../components/project/Knowledge.vue'
import Event from '../components/project/Event.vue'
import ClusterMonitor from '../components/project/Monitor.vue'
import ClusterOperation from '../components/project/Operation.vue'
import Audit from '../components/project/Audit.vue'
import { getProject, updateProject, type Project as ApiProject } from '@/apis/project'
import { deleteOperationScript } from '@/apis/operation'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import StatusTag from '@/components/common/StatusTag.vue'

// 接收路由参数
const props = defineProps<{
  id: string
}>()

const router = useRouter()
const { t } = useI18n()

// 当前选中的菜单项
const activeMenu = ref('topology')

const project = ref<ApiProject | null>(null)

const projectInfo = computed(() => {
  if (project.value) {
    return { name: project.value.name, status: t('project.status.normal'), team: t('project.team.unset') }
  }
  return { name: t('project.unknownName'), status: t('project.status.unknown'), team: t('project.team.unknown') }
})

// 菜单项配置(computed:title/description 随语言切换更新)
const menuItems = computed(() => [
  {
    id: 'topology',
    title: t('project.menu.topology.title'),
    icon: Share,
    description: t('project.menu.topology.desc')
  },
  {
    id: 'monitoring',
    title: t('project.menu.monitoring.title'),
    icon: Monitor,
    description: t('project.menu.monitoring.desc')
  },
  {
    id: 'events',
    title: t('project.menu.events.title'),
    icon: Warning,
    description: t('project.menu.events.desc')
  },
  {
    id: 'operation',
    title: t('project.menu.operation.title'),
    icon: Operation,
    description: t('project.menu.operation.desc')
  },
  {
    id: 'knowledge',
    title: t('project.menu.knowledge.title'),
    icon: DocumentCopy,
    description: t('project.menu.knowledge.desc')
  },
  {
    id: 'audit',
    title: t('project.menu.audit.title'),
    icon: Checked,
    description: t('project.menu.audit.desc')
  },
])

// 处理菜单点击
const handleMenuClick = (index: string) => {
  activeMenu.value = index
}

// 返回项目列表
const goBack = () => {
  router.push('/overview')
}

const loadProject = async () => {
  try {
    const p = await getProject(Number(props.id))
    project.value = p
  } catch {}
}

onMounted(() => {
  loadProject()
})

watch(() => props.id, () => {
  loadProject()
})

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref<FormInstance>()
const editForm = ref<{ name: string; desc: string }>({ name: '', desc: '' })
const editRules = computed<FormRules>(() => ({
  name: [{ required: true, message: t('project.form.namePlaceholder'), trigger: 'blur' }],
}))
const openEditDialog = () => {
  editForm.value = { name: project.value?.name || '', desc: project.value?.desc || '' }
  editDialogVisible.value = true
}
const submitEdit = async () => {
  if (!editFormRef.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return
  editLoading.value = true
  try {
    const msg = await updateProject(Number(props.id), { name: editForm.value.name, desc: editForm.value.desc })
    ElMessage.success(msg || t('project.updateSuccess'))
    editDialogVisible.value = false
    await loadProject()
  } catch (e: any) {
    ElMessage.error(e?.message || t('project.updateFailed'))
  } finally {
    editLoading.value = false
  }
}
const cancelEdit = () => {
  editDialogVisible.value = false
}

// 集群运维脚本删除:projectId 在父组件,删除与刷新逻辑由父组件承接
const operationRef = ref<InstanceType<typeof ClusterOperation>>()
const handleOperationDelete = async (scriptId: number | string) => {
  try {
    const msg = await deleteOperationScript(props.id, scriptId)
    ElMessage.success(msg || t('project.deleteSuccess'))
    operationRef.value?.loadScripts()
  } catch {
    // 失败提示由 request.ts 的 handleError 统一弹出,此处仅吞掉 rejection
  }
}
</script>

<template>
  <div class="h-full bg-gray-50 flex flex-col">
    <!-- 页面标题栏 -->
    <div class="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
      <div class="flex items-center">
        <el-button :icon="ArrowLeft" @click="goBack" class="mr-4 text-xl! font-bold text-black!" text>
          {{ $t('common.back') }}
        </el-button>
        <h2 class="text-black text-2xl font-bold">{{ projectInfo.name }}</h2>
        <StatusTag :status="projectInfo.status" size="small" class="ml-2 self-end" />
      </div>
      <div class="flex items-center space-x-4">
        <el-button type="primary" @click="openEditDialog">{{ $t('project.editProject') }}</el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 左侧边栏 -->
      <div class="w-64 bg-white shadow-md overflow-y-auto">
        <div class="p-4">
          <el-menu :default-active="activeMenu" class="border-none" @select="handleMenuClick">
            <el-menu-item v-for="item in menuItems" :key="item.id" :index="item.id" class="mb-2 rounded-md">
              <el-icon class="mr-3">
                <component :is="item.icon" />
              </el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="flex-1 bg-gray-50 overflow-y-auto p-3 pb-0">
        <!-- 知识库内容 -->
        <div v-if="activeMenu === 'knowledge'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <div class="h-full w-full rounded">
            <Knowledge :projectId="props.id" />
          </div>
        </div>

        <!-- 业务Topo内容 -->
        <div v-else-if="activeMenu === 'topology'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <div class="h-full w-full rounded">
            <Topology :projectId="props.id" />
          </div>
        </div>

        <!-- 集群事件内容 -->
        <div v-else-if="activeMenu === 'events'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <Event :projectId="props.id" />
        </div>

        <!-- 集群监控内容 -->
        <div v-else-if="activeMenu === 'monitoring'" class="bg-white rounded-lg shadow-sm p-6 ">
          <ClusterMonitor :projectId="props.id" />
        </div>

        <!-- 集群运维内容 -->
        <div v-else-if="activeMenu === 'operation'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <ClusterOperation ref="operationRef" :projectId="props.id" @delete="handleOperationDelete" />
        </div>

        <!-- 集群审计内容 -->
        <div v-else-if="activeMenu === 'audit'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <Audit :projectId="props.id" />
        </div>
      </div>
    </div>
    <el-dialog v-model="editDialogVisible" :title="$t('project.editProject')" width="500px" :lock-scroll="false">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px">
        <el-form-item :label="$t('project.form.name')" prop="name">
          <el-input v-model="editForm.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item :label="$t('project.form.desc')" prop="desc">
          <el-input v-model="editForm.desc" type="textarea" rows="4" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelEdit">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="editLoading" @click="submitEdit">{{ $t('project.update') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.el-menu-item.is-active {
  background-color: #f0f9ff;
  color: #1890ff;
}
</style>