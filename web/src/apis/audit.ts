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
