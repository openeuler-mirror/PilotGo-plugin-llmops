<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Document,
  Share,
  Warning,
  Monitor,
  ArrowLeft
} from '@element-plus/icons-vue'
import Topology from '../components/project/Topology.vue'

// 接收路由参数
const props = defineProps<{
  id: string
}>()

const router = useRouter()

// 当前选中的菜单项
const activeMenu = ref('topology')

// 根据ID获取项目信息
const projectInfo = computed(() => {
  const projectData = {
    1: { name: 'Nginx集群', status: '正常', team: '基础设施团队' },
    2: { name: 'Kafka集群', status: '警告', team: '基础设施团队' },
    3: { name: '业务1', status: '正常', team: '业务团队-1' },
    4: { name: 'Kubernetes集群', status: '错误', team: '基础设施团队' },
    5: { name: '业务2', status: '正常', team: '业务团队-2' },
    6: { name: '移动端应用', status: '警告', team: '移动端团队' }
  }
  const idNum = Number(props.id)
  const validKeys: (keyof typeof projectData)[] = [1, 2, 3, 4, 5, 6]
  return validKeys.includes(idNum as keyof typeof projectData)
    ? projectData[idNum as keyof typeof projectData]
    : { name: '未知项目', status: '未知', team: '未知团队' }
})

// 菜单项配置
const menuItems = [
  {
    id: 'topology',
    title: '业务Topo',
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
    id: 'knowledge',
    title: '知识库',
    icon: Document,
    description: '项目相关文档和知识管理'
  }
]

// 处理菜单点击
const handleMenuClick = (index: string) => {
  activeMenu.value = index
}

// 返回项目列表
const goBack = () => {
  router.push('/')
}
</script>

<template>
  <div class="h-full bg-gray-50 flex flex-col">
    <!-- 页面标题栏 -->
    <div class="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
      <div class="flex items-center">
        <el-button type="text" :icon="ArrowLeft" @click="goBack" class="mr-4">
          返回
        </el-button>
        <h2 class="text-black text-2xl font-bold">{{ projectInfo.name }} - 项目详情</h2>
        <el-tag :type="projectInfo.status === '正常' ? 'success' : projectInfo.status === '警告' ? 'warning' : 'danger'"
          size="small" class="ml-2 self-end">
          {{ projectInfo.status }}
        </el-tag>
      </div>
      <div class="flex items-center space-x-4">
        <el-button type="primary">编辑项目</el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 左侧边栏 -->
      <div class="w-64 bg-white shadow-md overflow-y-auto">
        <div class="p-4">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">功能模块</h2>
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
        <div v-if="activeMenu === 'knowledge'" class="bg-white rounded-lg shadow-sm p-6">
          <h2 class="text-xl font-semibold text-gray-800 mb-4">知识库</h2>
          <p class="text-gray-600 mb-6">这里是项目相关的文档和知识管理内容。</p>
          <el-empty description="知识库内容正在开发中" />
        </div>

        <!-- 业务Topo内容 -->
        <div v-else-if="activeMenu === 'topology'" class="bg-white rounded-lg shadow-sm p-6 h-full">
          <div class="h-full w-full border border-gray-200 rounded">
            <Topology :projectId="props.id" />
          </div>
        </div>

        <!-- 集群事件内容 -->
        <div v-else-if="activeMenu === 'events'" class="bg-white rounded-lg shadow-sm p-6">
          <h2 class="text-xl font-semibold text-gray-800 mb-4">集群事件</h2>
          <p class="text-gray-600 mb-6">这里是集群事件和告警信息展示。</p>
          <el-empty description="集群事件内容正在开发中" />
        </div>

        <!-- 集群监控内容 -->
        <div v-else-if="activeMenu === 'monitoring'" class="bg-white rounded-lg shadow-sm p-6">
          <h2 class="text-xl font-semibold text-gray-800 mb-4">集群监控</h2>
          <p class="text-gray-600 mb-6">这里是集群性能和资源监控展示。</p>
          <el-empty description="集群监控内容正在开发中" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.el-menu-item.is-active {
  background-color: #f0f9ff;
  color: #1890ff;
}

/* .project-title {
  color: #dc2626;
} */
</style>