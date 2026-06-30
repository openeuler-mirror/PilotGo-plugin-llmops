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

export async function deleteOperationScript(
  projectId: number | string,
  scriptId: number | string,
): Promise<string> {
  const res = await httpClient.delete<void>(`/api/project/${projectId}/operation/scripts/${scriptId}`)
  return res.message ?? ''
}

export interface OperationScriptPayload {
  name: string
  description?: string
  content?: string
  updatedBy?: string
}

export async function createOperationScript(
  projectId: number | string,
  payload: OperationScriptPayload,
): Promise<string> {
  // 前端驼峰 → 后端下划线
  const res = await httpClient.post<void>(`/api/project/${projectId}/operation/scripts`, {
    name: payload.name,
    description: payload.description,
    content: payload.content,
    updated_by: payload.updatedBy,
  })
  return res.message ?? ''
}

export async function updateOperationScript(
  projectId: number | string,
  scriptId: number | string,
  payload: OperationScriptPayload,
): Promise<string> {
  // 前端驼峰 → 后端下划线
  const res = await httpClient.put<void>(`/api/project/${projectId}/operation/scripts/${scriptId}`, {
    name: payload.name,
    description: payload.description,
    content: payload.content,
    updated_by: payload.updatedBy,
  })
  return res.message ?? ''
}
