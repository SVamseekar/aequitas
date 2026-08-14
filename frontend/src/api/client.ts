const BASE = "/api"

export async function fetchJson<T>(
  path: string,
  params?: Record<string, string>,
  init?: RequestInit,
): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }

  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (init?.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(url.toString(), {
    ...init,
    credentials: "include",
    headers,
  })
  if (res.status === 401) {
    // Session expired — leave AuthContext to clear on next /me
    throw new Error("Unauthorized")
  }
  if (!res.ok) {
    const err = new Error(`API ${res.status}: ${await res.text()}`) as Error & { status?: number }
    err.status = res.status
    throw err
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return fetchJson<T>(path, undefined, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return fetchJson<T>(path, undefined, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export async function apiDelete(path: string): Promise<void> {
  await fetchJson<void>(path, undefined, { method: "DELETE" })
}
