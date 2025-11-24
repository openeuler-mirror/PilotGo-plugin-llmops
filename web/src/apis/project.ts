import { httpClient } from './request'

export interface Project {
  id: number
  name: string
  desc: string
  created_at: string
  updated_at: string
}

export async function createProject(payload: { name: string; desc?: string }): Promise<string> {
  const res = await httpClient.post<void>('/api/project', payload)
  return res.message ?? ''
}

export async function deleteProject(id: number): Promise<string> {
  const res = await httpClient.delete<void>(`/api/project/${id}`)
  return res.message ?? ''
}

export async function listProjects(): Promise<Project[]> {
  const res = await httpClient.get<Project[]>('/api/project')
  return res.data ?? []
}

export async function getProject(id: number): Promise<Project> {
  const res = await httpClient.get<Project>(`/api/project/${id}`)
  if (!res.data) {
    throw new Error('empty data')
  }
  return res.data
}

export async function updateProject(id: number, payload: { name: string; desc?: string }): Promise<string> {
  const res = await httpClient.put<void>(`/api/project/${id}`, payload)
  return res.message ?? ''
}