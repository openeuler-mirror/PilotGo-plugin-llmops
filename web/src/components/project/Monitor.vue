<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ projectId: string | number }>()

const loading = ref(false)

const cpuLineRef = ref<HTMLDivElement | null>(null)
const memLineRef = ref<HTMLDivElement | null>(null)
const netLineRef = ref<HTMLDivElement | null>(null)
const alertsPieRef = ref<HTMLDivElement | null>(null)
const cpuBarRef = ref<HTMLDivElement | null>(null)

let cpuLineChart: echarts.ECharts | null = null
let memLineChart: echarts.ECharts | null = null
let netLineChart: echarts.ECharts | null = null
let alertsPieChart: echarts.ECharts | null = null
let cpuBarChart: echarts.ECharts | null = null

type MetricData = {
  times: string[]
  cpu: number[]
  mem: number[]
  netIn: number[]
  netOut: number[]
  alerts: { name: string; value: number }[]
  cpuTop: { name: string; value: number }[]
}

const data = ref<MetricData>({ times: [], cpu: [], mem: [], netIn: [], netOut: [], alerts: [], cpuTop: [] })

function sampleData(): MetricData {
  const times: string[] = []
  const cpu: number[] = []
  const mem: number[] = []
  const netIn: number[] = []
  const netOut: number[] = []
  const now = Date.now()
  for (let i = 23; i >= 0; i--) {
    const t = new Date(now - i * 3600000)
    const pad = (n: number) => n.toString().padStart(2, '0')
    times.push(`${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}:00`)
    cpu.push(Math.round(40 + Math.random() * 50))
    mem.push(Math.round(35 + Math.random() * 55))
    netIn.push(Math.round(200 + Math.random() * 300))
    netOut.push(Math.round(180 + Math.random() * 260))
  }
  const alerts = [
    { name: '错误', value: Math.round(5 + Math.random() * 10) },
    { name: '警告', value: Math.round(10 + Math.random() * 20) },
    { name: '信息', value: Math.round(30 + Math.random() * 40) }
  ]
  const cpuTop: { name: string; value: number }[] = []
  for (let i = 1; i <= 10; i++) cpuTop.push({ name: `节点${i}`, value: Math.round(30 + Math.random() * 70) })
  return { times, cpu, mem, netIn, netOut, alerts, cpuTop }
}

async function load() {
  loading.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/monitor/metrics`)
    if (res.ok) {
      const j = await res.json()
      const base = sampleData()
      const times = Array.isArray(j.times) ? j.times : base.times
      data.value = {
        times,
        cpu: Array.isArray(j.cpu) ? j.cpu : base.cpu,
        mem: Array.isArray(j.mem) ? j.mem : base.mem,
        netIn: Array.isArray(j.netIn) ? j.netIn : base.netIn,
        netOut: Array.isArray(j.netOut) ? j.netOut : base.netOut,
        alerts: Array.isArray(j.alerts) ? j.alerts : base.alerts,
        cpuTop: Array.isArray(j.cpuTop) ? j.cpuTop : base.cpuTop
      }
    } else {
      data.value = sampleData()
    }
  } catch {
    data.value = sampleData()
  } finally {
    loading.value = false
    update()
  }
}

function init() {
  if (cpuLineRef.value && !cpuLineChart) {
    cpuLineChart = echarts.init(cpuLineRef.value)
    cpuLineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 16, top: 32, bottom: 24 },
      xAxis: { type: 'category', data: data.value.times },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [{ name: 'CPU', type: 'line', smooth: true, data: data.value.cpu, itemStyle: { color: '#5B8FF9' }, areaStyle: {} }]
    })
  }
  if (memLineRef.value && !memLineChart) {
    memLineChart = echarts.init(memLineRef.value)
    memLineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 16, top: 32, bottom: 24 },
      xAxis: { type: 'category', data: data.value.times },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [{ name: '内存', type: 'line', smooth: true, data: data.value.mem, itemStyle: { color: '#61DDAA' }, areaStyle: {} }]
    })
  }
  if (netLineRef.value && !netLineChart) {
    netLineChart = echarts.init(netLineRef.value)
    netLineChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['入流量', '出流量'] },
      grid: { left: 24, right: 16, top: 32, bottom: 24 },
      xAxis: { type: 'category', data: data.value.times },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}MB' } },
      series: [
        { name: '入流量', type: 'line', smooth: true, data: data.value.netIn, itemStyle: { color: '#5AD8A6' } },
        { name: '出流量', type: 'line', smooth: true, data: data.value.netOut, itemStyle: { color: '#F6BD16' } }
      ]
    })
  }
  if (alertsPieRef.value && !alertsPieChart) {
    alertsPieChart = echarts.init(alertsPieRef.value)
    alertsPieChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{ type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: false, itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }, label: { show: true, formatter: '{b} {d}%' }, data: data.value.alerts }]
    })
  }
  if (cpuBarRef.value && !cpuBarChart) {
    cpuBarChart = echarts.init(cpuBarRef.value)
    cpuBarChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 16, top: 32, bottom: 24 },
      xAxis: { type: 'category', data: data.value.cpuTop.map(x => x.name), axisLabel: { interval: 0 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [{ type: 'bar', data: data.value.cpuTop.map(x => x.value), itemStyle: { color: '#5B8FF9' } }]
    })
  }
}

function update() {
  if (cpuLineChart) cpuLineChart.setOption({ xAxis: { data: data.value.times }, series: [{ data: data.value.cpu }] })
  if (memLineChart) memLineChart.setOption({ xAxis: { data: data.value.times }, series: [{ data: data.value.mem }] })
  if (netLineChart) netLineChart.setOption({ xAxis: { data: data.value.times }, series: [{ data: data.value.netIn }, { data: data.value.netOut }] })
  if (alertsPieChart) alertsPieChart.setOption({ series: [{ data: data.value.alerts }] })
  if (cpuBarChart) cpuBarChart.setOption({ xAxis: { data: data.value.cpuTop.map(x => x.name) }, series: [{ data: data.value.cpuTop.map(x => x.value) }] })
}

const observers: ResizeObserver[] = []

function observeResize() {
  const refs = [cpuLineRef, memLineRef, netLineRef, alertsPieRef, cpuBarRef]
  refs.forEach(r => {
    if (r.value) {
      const ro = new ResizeObserver(() => {
        if (cpuLineChart) cpuLineChart.resize()
        if (memLineChart) memLineChart.resize()
        if (netLineChart) netLineChart.resize()
        if (alertsPieChart) alertsPieChart.resize()
        if (cpuBarChart) cpuBarChart.resize()
      })
      ro.observe(r.value)
      observers.push(ro)
    }
  })
}

onMounted(() => {
  init()
  observeResize()
  load()
})

onBeforeUnmount(() => {
  observers.forEach(o => o.disconnect())
  if (cpuLineChart) { cpuLineChart.dispose(); cpuLineChart = null }
  if (memLineChart) { memLineChart.dispose(); memLineChart = null }
  if (netLineChart) { netLineChart.dispose(); netLineChart = null }
  if (alertsPieChart) { alertsPieChart.dispose(); alertsPieChart = null }
  if (cpuBarChart) { cpuBarChart.dispose(); cpuBarChart = null }
})

watch(() => props.projectId, () => {
  load()
})
</script>

<template>
  <div class="h-full w-full">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">集群监控</h2>
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-700 font-medium">CPU使用率趋势</span>
            <el-tag type="info" size="small" v-if="loading">加载中</el-tag>
          </div>
          <div ref="cpuLineRef" class="w-full h-64"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-700 font-medium">内存使用率趋势</span>
            <el-tag type="info" size="small" v-if="loading">加载中</el-tag>
          </div>
          <div ref="memLineRef" class="w-full h-64"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-700 font-medium">网络流量趋势</span>
          </div>
          <div ref="netLineRef" class="w-full h-64"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-700 font-medium">告警分布</span>
          </div>
          <div ref="alertsPieRef" class="w-full h-64"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :md="24">
        <el-card>
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-700 font-medium">主机CPU Top10</span>
          </div>
          <div ref="cpuBarRef" class="w-full h-72"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>