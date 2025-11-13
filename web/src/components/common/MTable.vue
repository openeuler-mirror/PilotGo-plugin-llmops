<script setup lang="ts">
const props = defineProps<{
  data: any[]
  currentPage: number
  totalPages: number
}>()

const emit = defineEmits<{
  (e: 'page-change', page: number): void
}>()

const handlePageChange = (page: number) => {
  emit('page-change', page)
}
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <el-table :data="props.data" border stripe class="w-full flex-1">
      <slot name="columns" />
    </el-table>
    <div class="mt-4 flex justify-end">
      <el-pagination
        background
        layout="prev, pager, next"
        :current-page="props.currentPage"
        :page-count="props.totalPages"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>