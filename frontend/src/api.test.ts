import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, type PayslipCreate } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  document.cookie = 'csrf_token=; Max-Age=0; path=/'
})

describe('API client', () => {
  it('sends all auth and payslip requests with their typed payloads', async () => {
    const fetchMock = vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ message: 'ok' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.login('owner', 'safe-password')
    await api.verifyOtp('owner', '123456')
    await api.me()
    await api.logout()
    await api.listPayslips()

    const payload: PayslipCreate = {
      employee_code: 'EMP-42',
      month: '2026-01',
      basic: 5000,
      other_allowances: 0,
      total_working_days: 30,
      days_paid: 28,
      deduction_lines: [],
    }
    await api.createPayslip(payload)

    expect(fetchMock).toHaveBeenCalledTimes(6)
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      '/api/v1/auth/login',
      '/api/v1/auth/verify-otp',
      '/api/v1/auth/me',
      '/api/v1/auth/logout',
      '/api/v1/payslip/payslips',
      '/api/v1/payslip/payslips',
    ])
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ username: 'owner', password: 'safe-password' }),
    })
    expect(fetchMock.mock.calls[5]?.[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('returns undefined for no-content responses and parses API error messages', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ code: 'invalid', detail: 'Bad request' }), {
          status: 400,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.logout()).resolves.toBeUndefined()
    await expect(api.me()).rejects.toMatchObject({
      status: 400,
      code: 'invalid',
      message: 'Bad request',
    } satisfies Partial<ApiError>)
  })

  it('uses plain-text error bodies when the response is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('upstream unavailable', { status: 502 })),
    )

    await expect(api.me()).rejects.toMatchObject({
      status: 502,
      message: 'upstream unavailable',
    })
  })
})
