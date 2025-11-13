<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import ProjectCard from '@/components/ProjectCard.vue'

const router = useRouter()

// 模拟项目数据
const projects = ref([
  {
    id: 1,
    name: 'Nginx集群',
    description: 'Nginx集群部署，提供高可用的反向代理服务',
    status: '正常',
    lastUpdate: '2024-01-15',
    team: '基础设施团队'
  },
  {
    id: 2,
    name: 'Kafka集群',
    description: 'Kafka集群部署，提供高可用的消息队列服务',
    status: '警告',
    lastUpdate: '2024-01-14',
    team: '基础设施团队'
  },
  {
    id: 3,
    name: '业务1',
    description: '业务1的相关项目',
    status: '正常',
    lastUpdate: '2024-01-10',
    team: '业务团队-1'
  },
  {
    id: 4,
    name: 'Kubernetes集群',
    description: 'Kubernetes集群部署，提供容器化应用的编排和管理',
    status: '错误',
    lastUpdate: '2024-01-12',
    team: '基础设施团队'
  },
  {
    id: 5,
    name: '业务2',
    description: '业务2的相关项目',
    status: '正常',
    lastUpdate: '2024-01-13',
    team: '业务团队-2'
  },
  {
    id: 6,
    name: '移动端应用',
    description: 'iOS和Android原生移动应用',
    status: '警告',
    lastUpdate: '2024-01-11',
    team: '移动端团队'
  }
])

// 处理查看项目详情
const handleViewProjectDetails = (projectId: number) => {
  console.log('查看项目详情:', projectId)
  // 导航到项目详情页，携带项目ID参数
  router.push(`/project/${projectId}`)
}
</script>

<template>
  <div class="h-full bg-gray-50 flex flex-col">
    <!-- 页面标题 - 固定高度 -->
    <div class="flex justify-between items-center py-6 shrink-0">
      <div class="flex-1"></div>
      <div class="text-center">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">项目概览</h1>
        <p class="text-gray-600">管理和监控您的所有项目</p>
      </div>
      <div class="flex-1 flex justify-end">
        <el-button type="primary" size="large" class="mr-3">
          <el-icon class="mr-2">
            <Plus />
          </el-icon>
          创建项目
        </el-button>
      </div>
    </div>

    <!-- 项目卡片网格 - 可滚动区域 -->
    <div class="flex-1 overflow-y-auto" style="padding-right: 200px; padding-left: 200px;">
      <el-row :gutter="24">
        <el-col v-for="project in projects" :key="project.id" :xs="24" :sm="12" :md="8" :lg="6"
          style="padding-bottom: 20px;">
          <ProjectCard v-bind="project" @view-details="handleViewProjectDetails" />
        </el-col>
      </el-row>
    </div>
  </div>
</template>
