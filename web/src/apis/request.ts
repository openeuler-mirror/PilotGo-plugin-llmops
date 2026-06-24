const config = {
  // Read from the VITE_API_BASE_URL env var; defaults to an empty string so the
  // client issues same-origin relative requests (e.g. "/api"), which the Vite
  // dev proxy forwards to the backend. Set an absolute URL to target a remote API.
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
}

// HTTP请求工具类
export interface ApiResponse<T = any> {
  message?: string
  data?: T
  error?: string
}

export interface PaginationResponse<T = any> {
  total: number
  page: number
  perpage: number
  data: T[]
}

class HttpClient {
  private baseURL: string

  constructor(baseURL: string = config.apiBaseUrl) {
    this.baseURL = baseURL
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
      throw error
    }
  }

  async get<T>(url: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    let fullUrl = url
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value))
        }
      })
      const queryString = searchParams.toString()
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
  }
}

export const httpClient = new HttpClient()
