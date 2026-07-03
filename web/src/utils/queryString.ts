/**
 * Build a URL query string from flat key/value params.
 * Skips undefined, null, and empty-string values.
 */
export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value))
    }
  })
  return searchParams.toString()
}

/** Append optional query params to a URL path or absolute URL. */
export function appendQueryString(url: string, params?: Record<string, unknown>): string {
  if (!params) {
    return url
  }
  const queryString = buildQueryString(params)
  if (!queryString) {
    return url
  }
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}${queryString}`
}
