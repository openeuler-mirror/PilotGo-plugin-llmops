<template>
  <el-tag :type="tagType" v-bind="$attrs">
    <slot>{{ status }}</slot>
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const STATUS_MAP: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  正常: 'success',
  警告: 'warning',
  错误: 'danger',
}

const tagType = computed(() => STATUS_MAP[props.status] ?? 'info')
</script>

<script lang="ts">
export default { inheritAttrs: false }
</script>
