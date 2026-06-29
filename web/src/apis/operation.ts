import { httpClient } from './request'

export interface OperationScript {
  id: number | string
  name: string
  description: string
  content?: string
  updatedBy: string
  updatedAt: string
}

export async function listOperationScripts(projectId: number | string, page?: number): Promise<OperationScript[]> {
  const res = await httpClient.get<any[]>(`/api/project/${projectId}/operation/scripts`, { page })
  const list = res.data ?? []
  // 后端下划线 → 前端驼峰映射
  return (Array.isArray(list) ? list : []).map((it: any) => ({
    id: it.id,
    name: it.name,
    description: it.description,
    content: it.content,
    updatedBy: it.updated_by ?? '',
    updatedAt: it.updated_at ?? '',
  }))
}
