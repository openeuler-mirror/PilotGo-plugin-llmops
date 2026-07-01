import { httpClient, type PaginationResponse } from './request'

export interface AuditItem {
    id: number | string
    time: string
    operator: string
    component: string
    description: string
}

// 后端 ListAuditByProjectID 返回 ResponsePage { page, perpage, total, data };
// data 已在 handler 映射为 time/operator/component/description,无需前端再映射。
export async function listProjectAuditLogs(
    projectId: number | string,
    page = 1,
    perpage = 20,
): Promise<PaginationResponse<AuditItem>> {
    const res = (await httpClient.get<AuditItem[]>(
        `/api/project/${projectId}/audit/logs`,
        { page, perpage },
    )) as unknown as PaginationResponse<AuditItem>
    return {
        page: res.page ?? page,
        perpage: res.perpage ?? perpage,
        total: res.total ?? 0,
        data: res.data ?? [],
    }
}

// 后端 ListAuditByFilters 打 /api/audit/logs,返回 ResponsePage { page, perpage, total, data }。
// 空串/undefined 由 httpClient.get 自动丢弃,后端 dao 亦跳过空条件,故 filters 可全传。
export async function listAuditByFilters(
    projectId: number | string,
    filters: { actor?: string; actionType?: string; target?: string },
    page = 1,
    perpage = 20,
): Promise<PaginationResponse<AuditItem>> {
    const res = (await httpClient.get<AuditItem[]>('/api/audit/logs', {
        project_id: projectId,
        actor: filters.actor,
        action_type: filters.actionType,   // camelCase 参数 → snake_case query key
        target: filters.target,
        page,
        perpage,
    })) as unknown as PaginationResponse<AuditItem>
    return {
        page: res.page ?? page,
        perpage: res.perpage ?? perpage,
        total: res.total ?? 0,
        data: res.data ?? [],
    }
}
