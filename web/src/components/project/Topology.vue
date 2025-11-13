<template>
  <div class="topology-container">
    <div ref="graphContainer" class="graph-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Graph } from '@antv/g6'

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const graphContainer = ref<HTMLDivElement | null>(null)
let graph: Graph | null = null

// 默认数据
const defaultData = {
  nodes: [
    { id: 'node1', label: '节点1', x: 100, y: 100 },
    { id: 'node2', label: '节点2', x: 300, y: 100 },
    { id: 'node3', label: '节点3', x: 200, y: 200 },
    { id: 'node4', label: '节点4', x: 400, y: 200 },
  ],
  edges: [
    { source: 'node1', target: 'node2', label: '连接1' },
    { source: 'node1', target: 'node3', label: '连接2' },
    { source: 'node2', target: 'node4', label: '连接3' },
    { source: 'node3', target: 'node4', label: '连接4' },
  ]
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
  })

  graph.setData(data)
  graph.render()

  // 添加事件监听
  graph.on('node:mouseenter', (evt: any) => {
    const { itemId } = evt
    if (itemId) {
      // TODO:
    }
  })

  graph.on('node:mouseleave', (evt: any) => {
    const { itemId } = evt
    if (itemId) {
      // TODO:
    }
  })
}

// 监听项目ID变化
watch(
  () => props.projectId,
  () => {
    initGraph()
  }
)

const loadTopologyData = async () => {
  try {
    const res = await fetch(`/api/projects/${props.projectId}/topology`)
    if (res.ok) {
      const json = await res.json()
      return json
    }
  } catch (e) { }
  return defaultData
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

// 暴露方法给父组件
defineExpose({
  getGraph: () => graph,
  refresh: async () => {
    if (graph) {
      const data = await loadTopologyData()
      data.nodes.forEach((node: any) => {
        node.type = 'circle'
      })
      graph.setData(data)
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
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>