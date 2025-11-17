<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
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
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

// 接收路由参数
const props = defineProps<{
  id: string
}>()

const router = useRouter()

// 当前选中的菜单项
const activeMenu = ref('topology')

const project = ref<ApiProject | null>(null)

const projectInfo = computed(() => {
  if (project.value) {
    return { name: project.value.name, status: '正常', team: '未设置' }
  }
  return { name: '未知项目', status: '未知', team: '未知团队' }
})

// 菜单项配置
const menuItems = [
  {
    id: 'topology',
    title: '业务拓扑',
    icon: Share,
    description: '业务拓扑结构和依赖关系'
  },
  {
    id: 'monitoring',
    title: '集群监控',
    icon: Monitor,
    description: '集群性能和资源监控'
  },
  {
    id: 'events',
    title: '集群事件',
    icon: Warning,
    description: '集群事件和告警信息'
  },
  {
    id: 'operation',
    title: '集群运维',
    icon: Operation,
    description: '集群运维'
  },
  {
    id: 'knowledge',
    title: '知识库',
    icon: DocumentCopy,
    description: '项目相关文档和知识管理'
  },
  {
    id: 'audit',
    title: '集群审计',
    icon: Checked,
    description: '集群操作审计记录'
  },
]

// 处理菜单点击
const handleMenuClick = (index: string) => {
  activeMenu.value = index
}

// 返回项目列表
const goBack = () => {
  router.push('/')
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
const editRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}
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
    ElMessage.success(msg || '更新成功')
    editDialogVisible.value = false
    await loadProject()
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  } finally {
    editLoading.value = false
  }
}
const cancelEdit = () => {
  editDialogVisible.value = false
}
</script>

<template>
  <div class="h-full bg-gray-50 flex flex-col">
    <!-- 页面标题栏 -->
    <div class="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
      <div class="flex items-center">
        <el-button :icon="ArrowLeft" @click="goBack" class="mr-4 text-xl! font-bold text-black!" text>
          返回
        </el-button>
        <h2 class="text-black text-2xl font-bold">{{ projectInfo.name }}</h2>
        <el-tag :type="projectInfo.status === '正常' ? 'success' : projectInfo.status === '警告' ? 'warning' : 'danger'"
          size="small" class="ml-2 self-end">
          {{ projectInfo.status }}
        </el-tag>
      </div>
      <div class="flex items-center space-x-4">
        <el-button type="primary" @click="openEditDialog">编辑项目</el-button>
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
          <ClusterOperation :projectId="props.id" />
        </div>

        <!-- 集群审计内容 -->
        <div v-else-if="activeMenu === 'audit'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <Audit :projectId="props.id" />
        </div>
      </div>
    </div>
    <el-dialog v-model="editDialogVisible" title="编辑项目" width="500px" :lock-scroll="false">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="editForm.name" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="项目描述" prop="desc">
          <el-input v-model="editForm.desc" type="textarea" rows="4" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelEdit">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="submitEdit">更新</el-button>
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