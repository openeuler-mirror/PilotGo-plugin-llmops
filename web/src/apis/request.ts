const config = {
  // API基础URL
  apiBaseUrl: '',
}

// HTTP请求工具类
export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}

export interface PaginationResponse<T = any> {
  total: number
  page: number
  page_size: number
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

    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(fullUrl, defaultOptions)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json() as ApiResponse<T>
      return result
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
}

export const httpClient = new HttpClient()