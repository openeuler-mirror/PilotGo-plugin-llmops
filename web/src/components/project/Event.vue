<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ projectId: string | number }>()

type Severity = '信息' | '警告' | '错误'
interface EventItem {
  id: string | number
  timestamp: string
  severity: Severity
  title: string
  description?: string
}

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const events = ref<EventItem[]>([])
const loading = ref(false)
const selectedDate = ref<string | null>(null)

const filteredEvents = computed(() => {
  if (!selectedDate.value) return events.value
  return events.value.filter(e => e.timestamp.slice(0, 10) === selectedDate.value)
})

const dateBuckets = computed(() => {
  const m = new Map<string, number>()
  for (const e of events.value) {
    const d = e.timestamp.slice(0, 10)
    m.set(d, (m.get(d) || 0) + 1)
  }
  const arr = Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  return { categories: arr.map(([d]) => d), counts: arr.map(([, c]) => c) }
})

const severityColor = (sev: Severity) => {
  if (sev === '错误') return '#F56C6C'
  if (sev === '警告') return '#E6A23C'
  return '#409EFF'
}

const severityTagType = (sev: Severity) => {
  if (sev === '错误') return 'danger'
  if (sev === '警告') return 'warning'
  return 'info'
}

const formatTime = (iso: string) => {
  const d = new Date(iso)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 24, right: 24, top: 32, bottom: 24 },
    xAxis: { type: 'category', data: dateBuckets.value.categories },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: dateBuckets.value.counts, itemStyle: { color: '#5B8FF9' } }]
  })
  chart.on('click', (params: any) => {
    if (params.componentType === 'series') {
      selectedDate.value = dateBuckets.value.categories[params.dataIndex] as (string | null)
    }
  })
}

const updateChart = () => {
  if (!chart) return
  chart.setOption({
    xAxis: { data: dateBuckets.value.categories },
    series: [{ data: dateBuckets.value.counts }]
  })
}

const sampleEvents = (): EventItem[] => {
  const now = new Date()
  const arr: EventItem[] = []
  for (let i = 0; i < 20; i++) {
    const d = new Date(now.getTime() - i * 21600000)
    const sev: Severity = i % 7 === 0 ? '错误' : i % 3 === 0 ? '警告' : '信息'
    arr.push({ id: i, timestamp: d.toISOString(), severity: sev, title: sev === '错误' ? '节点故障' : sev === '警告' ? '磁盘空间告警' : '任务完成', description: '' })
  }
  return arr
}

const loadEvents = async () => {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/events`)
    if (res.ok) {
      const data = await res.json()
      const list = Array.isArray(data) ? data : (data.items || data.events || [])
      events.value = list.map((x: any, i: number) => ({
        id: x.id ?? i,
        timestamp: x.timestamp ?? x.time ?? new Date().toISOString(),
        severity: (x.severity ?? x.level ?? '信息') as Severity,
        title: x.title ?? x.message ?? '事件',
        description: x.description ?? x.details ?? ''
      }))
    } else {
      events.value = sampleEvents()
    }
  } catch (e) {
    events.value = sampleEvents()
  } finally {
    loading.value = false
    if (!chart) initChart(); else updateChart()
  }
}

const clearFilter = () => { selectedDate.value = null }

const resizeObserver = new ResizeObserver(() => { if (chart) chart.resize() })

onMounted(() => {
  loadEvents()
  if (chartRef.value) resizeObserver.observe(chartRef.value)
})

onBeforeUnmount(() => {
  if (chartRef.value) resizeObserver.unobserve(chartRef.value)
  if (chart) { chart.dispose(); chart = null }
})

watch(() => props.projectId, () => { selectedDate.value = null; loadEvents() })
watch(events, () => updateChart())
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-800">集群事件</h2>
      <div class="flex items-center space-x-2">
        <el-button v-if="selectedDate" size="small" @click="clearFilter">清除日期筛选</el-button>
      </div>
    </div>
    <div class="bg-white rounded-lg shadow-sm p-4 h-[150px]">
      <div ref="chartRef" class="w-full h-full"></div>
    </div>
    <div class="mt-4 flex-1 overflow-y-auto bg-white rounded-lg shadow-sm p-4">
      <div class="flex items-center justify-between mb-2">
        <div class="text-gray-700">
          <span>事件时间线</span>
          <span v-if="selectedDate" class="ml-2 text-gray-500">日期 {{ selectedDate }}</span>
        </div>
        <el-tag type="info">共 {{ filteredEvents.length }} 条</el-tag>
      </div>
      <el-timeline>
        <el-timeline-item v-for="item in filteredEvents" :key="String(item.id)" :timestamp="formatTime(item.timestamp)" :color="severityColor(item.severity)">
          <div class="flex items-center">
            <el-tag :type="severityTagType(item.severity)" size="small" class="mr-2">{{ item.severity }}</el-tag>
            <span class="font-medium text-gray-800 mr-2">{{ item.title }}</span>
            <span class="text-gray-500 text-sm">{{ item.description }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>