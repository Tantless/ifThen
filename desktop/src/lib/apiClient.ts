const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8000'

type RawBody =
  | string
  | FormData
  | URLSearchParams
  | Blob
  | ArrayBuffer

type RequestBody = RawBody | Record<string, unknown> | unknown[] | null | undefined

function normalizePath(path: string): string {
  return path.startsWith('/') ? path : `/${path}`
}

function isBodyInitLike(body: RequestBody): body is RawBody {
  if (body == null) {
    return false
  }

  if (typeof body === 'string') {
    return true
  }

  if (typeof FormData !== 'undefined' && body instanceof FormData) {
    return true
  }

  if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) {
    return true
  }

  if (typeof Blob !== 'undefined' && body instanceof Blob) {
    return true
  }

  if (typeof ArrayBuffer !== 'undefined' && body instanceof ArrayBuffer) {
    return true
  }
  return false
}

function buildRequestInit(method: string, body?: RequestBody, init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers)
  let nextBody: RawBody | null | undefined

  if (body !== undefined) {
    if (isBodyInitLike(body)) {
      nextBody = body
    } else {
      headers.set('Content-Type', 'application/json')
      nextBody = JSON.stringify(body)
    }
  }

  return {
    ...init,
    method,
    headers,
    body: nextBody,
  }
}

export function createApiClient(fetchImpl: typeof fetch = fetch) {
  async function request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetchImpl(`${DEFAULT_API_ORIGIN}${normalizePath(path)}`, init)

    if (!response.ok) {
      const detail = typeof response.text === 'function' ? (await response.text()).trim() : ''
      throw new Error(`API request failed: ${response.status}${detail ? ` ${detail}` : ''}`)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  }

  return {
    get: <T>(path: string, init?: RequestInit) => request<T>(path, buildRequestInit('GET', undefined, init)),
    put: <T>(path: string, body: RequestBody, init?: RequestInit) =>
      request<T>(path, buildRequestInit('PUT', body, init)),
    post: <T>(path: string, body?: RequestBody, init?: RequestInit) =>
      request<T>(path, buildRequestInit('POST', body, init)),
    delete: <T = void>(path: string, init?: RequestInit) =>
      request<T>(path, buildRequestInit('DELETE', undefined, init)),
  }
}

export const apiClient = createApiClient()
