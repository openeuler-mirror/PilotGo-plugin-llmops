export interface AuditItem {
    id: number | string
    time: string
    operator: string
    component: string
    description: string
}

export async function listProjectAuditLogs(projectId: number | string, page?: number): Promise<AuditItem[]> {
    const url = `/api/project/${projectId}/audit/logs${page ? `?page=${page}` : ''}`
    const res = await fetch(url)
    if (!res.ok) return []
    const data = await res.json()
    if (Array.isArray(data)) return data as AuditItem[]
    if (data && Array.isArray(data.data)) return data.data as AuditItem[]
    return []
}
