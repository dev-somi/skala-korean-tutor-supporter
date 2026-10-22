import type { ApiErrorBody } from './types'

/** backend가 돌려준 오류. retryable이면 화면에 [다시 시도]를 보여 준다. */
export class ApiError extends Error {
  readonly code: string
  readonly retryable: boolean
  readonly status: number

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.retryable = body.retryable
  }
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init
  const res = await fetch(`/api${path}`, {
    ...rest,
    headers: { ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}), ...rest.headers },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  if (!res.ok) {
    let body: ApiErrorBody = { code: 'HTTP_' + res.status, message: res.statusText, retryable: res.status >= 500 }
    try {
      body = await res.json()
    } catch {
      // 본문이 JSON이 아니면 기본값을 쓴다
    }
    throw new ApiError(res.status, body)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const get = <T>(path: string) => api<T>(path)
export const post = <T>(path: string, json?: unknown) => api<T>(path, { method: 'POST', json })
export const put = <T>(path: string, json?: unknown) => api<T>(path, { method: 'PUT', json })
export const patch = <T>(path: string, json?: unknown) => api<T>(path, { method: 'PATCH', json })
export const del = (path: string) => api<void>(path, { method: 'DELETE' })
