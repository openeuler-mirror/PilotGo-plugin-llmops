<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface Props {
  projectId: string | number
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'submit', payload: Array<{ hostId: string | number; processes: string[] }>): void
}>()

type Host = { id: string | number; name: string; ip?: string }
type Rule = { id: number; hostId: string | number | ''; processes: string[]; processOptions: string[]; loading: boolean }

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v)
})

const hosts = ref<Host[]>([])
const loadingHosts = ref(false)
const rules = ref<Rule[]>([])

const loadHosts = async () => {
  loadingHosts.value = true
  try {
    const res = await fetch(`/api/projects/${props.projectId}/hosts`)
    if (res.ok) {
      const list = await res.json()
      hosts.value = Array.isArray(list) ? list : []
    } else {
      hosts.value = [
        { id: 'h-1', name: '主机A', ip: '10.0.0.1' },
        { id: 'h-2', name: '主机B', ip: '10.0.0.2' },
        { id: 'h-3', name: '主机C', ip: '10.0.0.3' }
      ]
    }
  } catch {
    hosts.value = [
      { id: 'h-1', name: '主机A', ip: '10.0.0.1' },
      { id: 'h-2', name: '主机B', ip: '10.0.0.2' },
      { id: 'h-3', name: '主机C', ip: '10.0.0.3' }
    ]
  } finally {
    loadingHosts.value = false
  }
}

const addRule = () => {
  rules.value.push({ id: Date.now() + Math.floor(Math.random() * 1000), hostId: '', processes: [], processOptions: [], loading: false })
}

const removeRule = (index: number) => {
  rules.value.splice(index, 1)
}

const loadProcessesForRule = async (rule: Rule) => {
  rule.loading = true
  try {
    const res = await fetch(`/api/hosts/${rule.hostId}/processes`)
    if (res.ok) {
      const list = await res.json()
      rule.processOptions = Array.isArray(list) ? list.map((x: any) => String(x.name || x)) : []
    } else {
      rule.processOptions = ['nginx', 'mysql', 'redis', 'java', 'python', 'node']
    }
  } catch {
    rule.processOptions = ['nginx', 'mysql', 'redis', 'java', 'python', 'node']
  } finally {
    rule.loading = false
  }
}

const handleHostChange = (rule: Rule, hostId: string | number) => {
  rule.processes = []
  rule.processOptions = []
  if (hostId !== '') loadProcessesForRule(rule)
}

watch(() => props.visible, v => {
  if (v) {
    if (!hosts.value.length) loadHosts()
    if (!rules.value.length) addRule()
  } else {
    rules.value = []
  }
})

const canSubmit = computed(() => rules.value.some(r => r.hostId !== '' && r.processes.length > 0))

const handleCancel = () => {
  emit('update:visible', false)
}

const handleConfirm = () => {
  const payload = rules.value.filter(r => r.hostId !== '' && r.processes.length > 0).map(r => ({ hostId: r.hostId as string | number, processes: r.processes.slice() }))
  if (!payload.length) return
  emit('submit', payload)
}
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="$t('topology.config')" width="720px" :lock-scroll="false">
    <div class="flex items-center justify-between mb-3">
      <span class="text-gray-700">{{ $t('topology.ruleList') }}</span>
      <el-button type="primary" size="small" @click="addRule">{{ $t('topology.addRule') }}</el-button>
    </div>
    <el-form label-width="80px">
      <div v-for="(rule, idx) in rules" :key="rule.id" class="mb-2">
        <el-row :gutter="12" align="middle">
          <el-col :span="10">
            <el-form-item :label="$t('topology.host')">
              <el-select v-model="rule.hostId" :placeholder="$t('topology.selectHost')" filterable :loading="loadingHosts" class="w-full" @change="(val:any) => handleHostChange(rule, val)">
                <el-option v-for="h in hosts" :key="String(h.id)" :label="h.ip ? `${h.name} (${h.ip})` : h.name" :value="h.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('topology.process')">
              <el-select v-model="rule.processes" multiple filterable :disabled="!rule.hostId" :placeholder="$t('topology.selectProcess')" :loading="rule.loading" class="w-full">
                <el-option v-for="p in rule.processOptions" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="2" class="flex items-center">
            <el-button type="danger" text @click="removeRule(idx)">{{ $t('common.delete') }}</el-button>
          </el-col>
        </el-row>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="handleCancel">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" :disabled="!canSubmit" @click="handleConfirm">{{ $t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
</style>
