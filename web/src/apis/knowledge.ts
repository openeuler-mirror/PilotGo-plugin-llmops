import { httpClient } from './request'

export interface KnowledgeFile {
  id?: number
  filename: string
  fileType: string
  uploadedAt: string
  uploader: string
  description: string
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
  return await httpClient.getBlob('/api/knowledge/download', { object })
}

// 从文件名后缀推导文件类型(后端无此字段);取最后一个 "." 后的小写扩展名,无后缀则空
function extOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(dot + 1).toLowerCase() : ''
}

export async function listKnowledgeFiles(projectId: number | string, page?: number): Promise<KnowledgeFile[]> {
  const res = await httpClient.get<any[]>(`/api/project/${projectId}/knowledge/files`, { page })
  const list = res.data ?? []
  // 后端下划线 → 前端驼峰映射;fileType 从 filename 后缀推导
  return (Array.isArray(list) ? list : []).map((it: any) => {
    const filename = it.file_name ?? ''
    return {
      id: it.id,
      filename,
      fileType: extOf(filename),
      uploadedAt: it.created_at ?? '',
      uploader: it.uploader ?? '',
      description: it.desc ?? '',
    }
  })
}
