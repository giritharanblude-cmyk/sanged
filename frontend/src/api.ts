import type { components, paths as OpenApiPaths } from './generated/api'

type ApiPath = keyof OpenApiPaths
type Schemas = components['schemas']

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

// The response and request shapes come from the generated OpenAPI client
// (R-14). Money fields are strings on the wire (R-05), so the frontend
// never has to reformat a float it received.
export type Payslip = Schemas['PayslipOut']

// openapi-typescript emits a field that has a server-side default as a
// required property, so the generated PayslipCreate demands values the UI
// has no reason to send. Split it into the fields the caller must provide
// and the ones the API defaults.
type PayslipCreateRequired = Pick<
  Schemas['PayslipCreate'],
  'employee_code' | 'month' | 'total_working_days' | 'days_paid' | 'basic'
>
type PayslipCreateOptional = Partial<
  Pick<
    Schemas['PayslipCreate'],
    | 'employee_name'
    | 'other_allowances'
    | 'deduction_lines'
    | 'payment_mode'
    | 'designation'
    | 'date_of_issue'
    | 'date_of_joining'
    | 'aadhaar'
  >
>
export type PayslipCreate = PayslipCreateRequired & PayslipCreateOptional

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