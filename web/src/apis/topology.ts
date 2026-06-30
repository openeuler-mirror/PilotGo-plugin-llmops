import { httpClient } from './request'

export interface TopologyConfig {
  id: number | string
  projectId: number | string
  hostId: string
  process: string
  createdAt: string
  updatedAt: string
}

export async function listTopologyConfig(projectId: number | string): Promise<TopologyConfig[]> {
  const res = await httpClient.get<any[]>('/api/topology', { project_id: projectId })
  const list = res.data ?? []
  // 后端下划线 → 前端驼峰映射
  return (Array.isArray(list) ? list : []).map((it: any) => ({
    id: it.id,
    projectId: it.project_id,
    hostId: it.host_id ?? '',
    process: it.process ?? '',
    createdAt: it.created_at ?? '',
    updatedAt: it.updated_at ?? '',
  }))
}
