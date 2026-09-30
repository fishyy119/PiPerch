interface ApiErrorBody {
  error?: { code?: string; message?: string; details?: unknown }
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown

  constructor(status: number, body: ApiErrorBody) {
    super(body.error?.message ?? `请求失败（HTTP ${String(status)}）`)
    this.name = 'ApiError'
    this.status = status
    this.code = body.error?.code ?? 'http_error'
    this.details = body.error?.details
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { body, ...init } = options
  const headers = new Headers(init.headers)
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  const response = await fetch(url, {
    ...init,
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      // 非 JSON 错误仍由统一 ApiError 表示。
    }
    throw new ApiError(response.status, body)
  }
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T
  }
  return (await response.json()) as T
}

export const api = {
  get<T>(url: string): Promise<T> {
    return request<T>(url)
  },
  post<T>(url: string, body?: unknown): Promise<T> {
    return request<T>(url, { method: 'POST', body })
  },
  put<T>(url: string, body?: unknown): Promise<T> {
    return request<T>(url, { method: 'PUT', body })
  },
  delete<T>(url: string): Promise<T> {
    return request<T>(url, { method: 'DELETE' })
  },
}
