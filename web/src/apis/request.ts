import { ElMessage } from 'element-plus'
import { buildQueryString } from '../utils/queryString'

const config = {
  // Read from the VITE_API_BASE_URL env var; defaults to an empty string so the
  // client issues same-origin relative requests (e.g. "/api"), which the Vite
  // dev proxy forwards to the backend. Set an absolute URL to target a remote API.
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
}

/**
 * Unified API response envelope shared by all api modules (project / knowledge /
 * audit / ...).
 *
 * Mirrors the server response helpers in `server/http/handler/common.go`. A
 * single response only ever carries one of these fields, so all are optional:
 *   - Response(data)      -> { data }      success carrying a payload
 *   - ResponseOK(msg)     -> { message }   success carrying only a message
 *   - ResponseError(code) -> { error }     failure (sent with a non-2xx status)
 *
 * `T` is the type of the `data` payload.
 */
export interface ApiResponse<T = unknown> {
  data?: T
  message?: string
  error?: string
}

/**
 * Paginated API response envelope.
 *
 * Mirrors `ResponsePage(page, perPage, total, data)` in
 * `server/http/handler/common.go`, which returns the pagination metadata at the
 * top level alongside the `data` array:
 *   { page, perpage, total, data }
 *
 * `T` is the element type of the `data` array.
 */
export interface PaginationResponse<T = unknown> {
  page: number
  perpage: number
  total: number
  data: T[]
}

// HTTP请求工具类
class HttpClient {
  private baseURL: string

  constructor(baseURL: string = config.apiBaseUrl) {
    this.baseURL = baseURL
  }

  /**
   * Centralized error reporter: surfaces a single toast for any failed request
   * (network error, non-2xx response, or a backend `{ error }` envelope).
   *
   * The thrown Error already carries the backend-provided message (extracted
   * from the response's `error` / `message` field), so it is preferred here.
   * Network-level failures and unknown errors fall back to a generic message.
   */
  private handleError(error: unknown): void {
    let message: string
    if (error instanceof TypeError) {
      // fetch() rejects with a TypeError on network-level failures
      // (offline, DNS failure, connection refused, CORS, ...).
      message = '网络异常，请检查网络连接后重试'
    } else if (error instanceof Error && error.message) {
      message = error.message
    } else {
      message = '请求失败，请稍后重试'
    }
    ElMessage.error(message)
  }

  private async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const fullUrl = `${this.baseURL}${url}`
    const isForm = !!(options as any).body && (options as any).body instanceof FormData
    const headers: Record<string, string> = {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers as any),
    }
    const defaultOptions: RequestInit = { ...options, headers }

    try {
      const response = await fetch(fullUrl, defaultOptions)
      const contentType = response.headers.get('Content-Type') || ''
      const isJson = contentType.includes('application/json')
      const payload = isJson ? await response.json() : undefined
      if (!response.ok) {
        const msg = payload && (payload.error || payload.message) ? (payload.error || payload.message) : `HTTP ${response.status}`
        throw new Error(msg)
      }
      return (payload ?? {}) as ApiResponse<T>
    } catch (error) {
      this.handleError(error)
      throw error
    }
  }

  async get<T>(url: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    let fullUrl = url
    if (params) {
      const queryString = buildQueryString(params)
      if (queryString) {
        fullUrl += `?${queryString}`
      }
    }

    return this.request<T>(fullUrl, {
      method: 'GET',
    })
  }

  async post<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      method: 'DELETE',
    })
  }

  async postForm<T>(url: string, form: FormData): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      method: 'POST',
      body: form,
    })
  }

  async getBlob(url: string): Promise<Blob> {
    const fullUrl = `${this.baseURL}${url}`
    try {
      const res = await fetch(fullUrl, { method: 'GET' })
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try {
          const ct = res.headers.get('Content-Type') || ''
          if (ct.includes('application/json')) {
            const json = await res.json()
            if (json && (json.error || json.message)) msg = json.error || json.message
          }
        } catch {}
        throw new Error(msg)
      }
      return await res.blob()
    } catch (error) {
      this.handleError(error)
      throw error
    }
  }
}

export const httpClient = new HttpClient()
