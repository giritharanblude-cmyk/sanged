import type { paths as OpenApiPaths } from './generated/api'

type ApiPath = keyof OpenApiPaths

const apiPaths = {
  login: '/api/v1/auth/login',
  verifyOtp: '/api/v1/auth/verify-otp',
  me: '/api/v1/auth/me',
  logout: '/api/v1/auth/logout',
  listPayslips: '/api/v1/payslip/payslips',
  createPayslip: '/api/v1/payslip/payslips',
} as const satisfies Record<string, ApiPath>

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
  const method = init.method?.toUpperCase() ?? 'GET'
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  }
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = document.cookie
      .split(';')
      .map((cookie) => cookie.trim())
      .find((cookie) => cookie.startsWith('csrf_token='))
      ?.slice('csrf_token='.length)
    if (csrfToken) headers['x-csrf-token'] = decodeURIComponent(csrfToken)
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

export interface PayslipCreate {
  employee_code: string
  employee_name?: string
  month: string
  basic: number
  other_allowances: number
  total_working_days: number
  days_paid: number
  deduction_lines: { kind: 'deduction'; label: string; amount: number }[]
}

export const api = {
  login: (username: string, password: string) =>
    request<{ message: string }>(apiPaths.login, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  verifyOtp: (username: string, otp: string) =>
    request<{ user: { username: string; role: string }; message: string }>(
      apiPaths.verifyOtp,
      { method: 'POST', body: JSON.stringify({ username, otp }) },
    ),

  me: () => request<{ username: string; role: string }>(apiPaths.me),

  logout: () => request<{ message: string }>(apiPaths.logout, { method: 'POST' }),

  listPayslips: () => request<Payslip[]>(apiPaths.listPayslips),

  createPayslip: (payload: PayslipCreate) =>
    request<Payslip>(apiPaths.createPayslip, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}