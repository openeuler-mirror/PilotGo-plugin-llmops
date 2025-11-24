import { httpClient } from './request'

export interface AuditItem {
    id: number | string
    time: string
    operator: string
    component: string
    description: string
}

export async function listProjectAuditLogs(projectId: number | string, page?: number): Promise<AuditItem[]> {
    const res = await httpClient.get<AuditItem[]>(`/api/project/${projectId}/audit/logs`, { page })
    return res.data ?? []
}
