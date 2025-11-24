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
  const res = await httpClient.postForm<{ object: string }>('/api/knowledge/upload', fd)
  return res.data?.object ?? ''
}

export async function presignKnowledge(object: string, expiry?: number): Promise<string> {
  const res = await httpClient.get<{ url: string }>(
    '/api/knowledge/link',
    { object, expiry }
  )
  return res.data?.url ?? ''
}

export async function deleteKnowledge(id: number): Promise<string> {
  const res = await httpClient.delete<void>(`/api/knowledge/${id}`)
  return res.message ?? ''
}

export async function downloadKnowledge(object: string): Promise<Blob> {
  return await httpClient.getBlob(`/api/knowledge/download?object=${encodeURIComponent(object)}`)
}

export async function listKnowledgeFiles(projectId: number | string, page?: number): Promise<any> {
  const res = await httpClient.get<any>(`/api/project/${projectId}/knowledge/files`, { page })
  return res.data
}
