import { httpClient } from './request'

export interface KnowledgeItem {
  id: number
  project_id: number
  object: string
  file_name: string
  uploader: string
  desc: string
  created_at: string
  updated_at: string
}

export async function uploadKnowledge(params: {
  projectId: number
  file: File
  object?: string
  uploader?: string
  desc?: string
}): Promise<string> {
  const fd = new FormData()
  fd.append('project_id', String(params.projectId))
  if (params.object) fd.append('object', params.object)
  if (params.uploader) fd.append('uploader', params.uploader)
  if (params.desc) fd.append('desc', params.desc)
  fd.append('file', params.file)
  const res = await fetch('/api/knowledge/upload', { method: 'POST', body: fd })
  if (!res.ok) throw new Error(String(res.status))
  const json = await res.json()
  return (json && json.data && json.data.object) ? json.data.object : ''
}

export async function presignKnowledge(object: string, expiry?: number): Promise<string> {
  const res = await httpClient.get<{ url: string }>(
    '/api/knowledge/link',
    { object, expiry }
  )
  const data = res.data as any
  if (!data) return ''
  return (data as any).url ?? ''
}

export async function deleteKnowledge(id: number): Promise<string> {
  const res = await httpClient.delete<void>(`/api/knowledge/${id}`)
  return res.message
}

export async function downloadKnowledge(object: string): Promise<Blob> {
  const res = await fetch(`/api/knowledge/download?object=${encodeURIComponent(object)}`)
  if (!res.ok) throw new Error(String(res.status))
  return await res.blob()
}

export async function listKnowledgeFiles(projectId: number | string, page?: number): Promise<any> {
  const res = await httpClient.get<any>(`/api/projects/${projectId}/knowledge/files`, { page })
  return res.data
}
