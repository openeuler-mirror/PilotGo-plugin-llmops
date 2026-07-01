<template>
  <div class="topology-container flex flex-col">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">{{ $t('topology.title') }}</h2>
      <el-button type="primary" @click="openConfig">{{ $t('topology.config') }}</el-button>
    </div>
    <div class="flex flex-1 min-h-0 gap-4">
      <div ref="graphContainer" class="graph-container flex-1 min-w-0"></div>
      <div class="w-60 shrink-0 bg-white rounded-lg shadow-sm p-4 overflow-y-auto">
        <template v-if="selectedNode">
          <div class="mb-3">
            <div class="text-xs text-gray-500">{{ $t('topology.detail.name') }}</div>
            <div class="text-sm font-medium">{{ selectedNode.name }}</div>
          </div>
          <div class="mb-3">
            <div class="text-xs text-gray-500">{{ $t('topology.detail.type') }}</div>
            <div class="text-sm">{{ selectedNode.type }}</div>
          </div>
          <div v-if="selectedNode.host" class="mb-3">
            <div class="text-xs text-gray-500">{{ $t('topology.detail.host') }}</div>
            <div class="text-sm">{{ selectedNode.host }}</div>
          </div>
        </template>
        <div v-else class="text-sm text-gray-400">{{ $t('topology.detail.placeholder') }}</div>
      </div>
    </div>
    <TopologyConfig v-model:visible="configVisible" :projectId="props.projectId" @submit="onConfigSubmit" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Graph, type GraphData as G6GraphData } from '@antv/g6'
import TopologyConfig from './TopologyConfig.vue'
import { ElMessage } from 'element-plus'
import { listTopologyConfig } from '@/apis/topology'
import { configRowsToGraph, type GraphData } from '@/utils/topologyGraph'

const { t } = useI18n()

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const graphContainer = ref<HTMLDivElement | null>(null)
let graph: Graph | null = null
const configVisible = ref(false)

// 当前选中节点的详情（点击节点时填充,点击空白/切项目时清空）
const selectedNode = ref<{ name: string; type: string; host?: string } | null>(null)

// 从 node id 解析详情:按 id 前缀判类型;proc 节点查入边 source 得所属 host。
const buildNodeDetail = (id: string) => {
  const nd = graph?.getNodeData(id)
  const name = (nd?.data?.label as string) ?? ''
  if (id.startsWith('project-')) {
    return { name, type: t('topology.detail.typeProject') }
  }
  if (id.startsWith('host-')) {
    return { name, type: t('topology.detail.typeHost') }
  }
  // proc 节点:入边 source 就是其 host node id
  const parentEdge = graph?.getEdgeData().find((e: any) => e.target === id)
  const hostId = parentEdge?.source as string | undefined
  const hostLabel = hostId ? ((graph?.getNodeData(hostId)?.data?.label as string) ?? '') : ''
  return { name, type: t('topology.detail.typeProcess'), host: hostLabel }
}

// 初始化图形
const initGraph = async () => {
  if (!graphContainer.value) return

  // 销毁已存在的图形实例
  if (graph) {
    graph.destroy()
  }

  // 创建图形实例
  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight,
    layout: {
      type: 'dagre',
      preventOverlap: true,
      nodeSize: 40,
    },
    node: {
      style: {
        labelText: (d: any) => (d.data?.label as string) ?? '',
        fill: '#C6E5FF',
        stroke: '#5B8FF9',
        lineWidth: 2,
      },
    },
    edge: {
      type: 'polyline',
      style: {
        stroke: '#e2e2e2',
        lineWidth: 2,
        endArrow: (datum:any) => datum.data.hasArrow
      },
    },
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      'drag-element',
      {
        type: 'hover-activate',
        degree: 1,
      },
    ],
    animation: true,
  })

  // 加载数据
  const data = await loadTopologyData()

  // 设置节点类型
  data.nodes.forEach((node: any) => {
    node.type = 'circle'
    node.data = { label: node.label }   // 把顶层 label 收进 G6 约定的 data，供 labelText 回调取用
  })

  graph.setData(data as unknown as G6GraphData)
  graph.render()

  // 添加事件监听
  graph.on('node:click', (evt: any) => {
    const id = evt.target?.id as string | undefined
    if (id) {
      selectedNode.value = buildNodeDetail(id)
    }
  })

  graph.on('canvas:click', () => {
    selectedNode.value = null
  })
}

// 监听项目ID变化
watch(
  () => props.projectId,
  () => {
    selectedNode.value = null
    initGraph()
  }
)

const loadTopologyData = async (): Promise<GraphData> => {
  try {
    const rows = await listTopologyConfig(props.projectId)
    return configRowsToGraph(rows, props.projectId)
  } catch {
    // 请求层（request.ts）失败时已弹过错误提示，这里不再弹避免双 toast，
    // 仅返回仅根节点的兜底图。
    return configRowsToGraph([], props.projectId)
  }
}

// 监听容器大小变化
const resizeObserver = new ResizeObserver(() => {
  if (graph && graphContainer.value) {
    const { clientWidth, clientHeight } = graphContainer.value
    graph.resize(clientWidth, clientHeight)
  }
})

onMounted(() => {
  initGraph()
  if (graphContainer.value) {
    resizeObserver.observe(graphContainer.value)
  }
})

onBeforeUnmount(() => {
  if (graph) {
    graph.destroy()
    graph = null
  }
  if (graphContainer.value) {
    resizeObserver.unobserve(graphContainer.value)
  }
})

const openConfig = () => {
  configVisible.value = true
}

const onConfigSubmit = (payload: Array<{ hostId: string | number; processes: string[] }>) => {
  configVisible.value = false
  ElMessage.success(t('topology.updateSuccess'))
}

// 暴露方法给父组件
defineExpose({
  getGraph: () => graph,
  refresh: async () => {
    if (graph) {
      const data = await loadTopologyData()
      data.nodes.forEach((node: any) => {
        node.type = 'circle'
        node.data = { label: node.label }   // 把顶层 label 收进 G6 约定的 data，供 labelText 回调取用
      })
      graph.setData(data as unknown as G6GraphData)
      graph.render()
    }
  },
  fitView: () => {
    // if (graph) {
    //   graph.fitView({
    //     padding: 20,
    //   })
    // }
  },
})
</script>

<style scoped>
.topology-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.graph-container {
  height: 100%;
  overflow: hidden;
}
</style>
