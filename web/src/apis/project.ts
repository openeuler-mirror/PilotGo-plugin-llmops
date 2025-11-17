import { httpClient } from './request'

export interface Project {
  id: number
  name: string
  desc: string
  created_at: string
  updated_at: string
}

export async function createProject(payload: { name: string; desc?: string }): Promise<string> {
  const res = await httpClient.post<void>('/api/projects', payload)
  return res.message
}

export async function deleteProject(id: number): Promise<string> {
  const res = await httpClient.delete<void>(`/api/projects/${id}`)
  return res.message
}

export async function listProjects(): Promise<Project[]> {
  const res = await httpClient.get<Project[]>('/api/projects')
  return res.data ?? []
}

export async function getProject(id: number): Promise<Project> {
  const res = await httpClient.get<Project>(`/api/projects/${id}`)
  if (!res.data) {
    throw new Error('empty data')
  }
  return res.data
}

export async function updateProject(id: number, payload: { name: string; desc?: string }): Promise<string> {
  const res = await httpClient.put<void>(`/api/projects/${id}`, payload)
  return res.message
}