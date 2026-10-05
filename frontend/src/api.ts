export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

// The API authenticates with an httpOnly `session` cookie set by
// /api/v1/auth/verify-otp, so there is no token for JS to hold. Same-origin
// fetch sends the cookie automatically; `same-origin` keeps it off other hosts.
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  }

  const res = await fetch(path, { ...init, headers, credentials: 'same-origin' })
  if (res.status === 204) return undefined as T

  const text = await res.text()
  let body: Record<string, unknown> = {}
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = { detail: text }
    }
  }

  if (!res.ok) {
    throw new ApiError(
      res.status,
      (body.code as string) ?? 'error',
      (body.detail as string) ?? (body.message as string) ?? `Request failed (${res.status})`,
    )
  }
  return body as T
}

export interface Payslip {
  id: string
  employee_code: string | null
  month: string
  status: string
  gross: number
  total_deductions: number
  net: number
  net_in_words: string
}

export const api = {
  login: (username: string, password: string) =>
    request<{ message: string }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  verifyOtp: (username: string, otp: string) =>
    request<{ user: { username: string; role: string }; message: string }>(
      '/api/v1/auth/verify-otp',
      { method: 'POST', body: JSON.stringify({ username, otp }) },
    ),

  me: () => request<{ username: string; role: string }>('/api/v1/auth/me'),

  logout: () => request<{ message: string }>('/api/v1/auth/logout', { method: 'POST' }),

  listPayslips: () => request<Payslip[]>('/api/v1/payslip/payslips'),

  createPayslip: (payload: unknown) =>
    request<Payslip>('/api/v1/payslip/payslips', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}