import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App } from './App'
import { api, ApiError } from './api'
import { LoginView } from './views/LoginView'
import { OtpView } from './views/OtpView'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  document.cookie = 'csrf_token=; Max-Age=0; path=/'
})

describe('authentication screens', () => {
  it('runs login and OTP verification before showing the authenticated shell', async () => {
    vi.spyOn(api, 'me').mockRejectedValue(new ApiError(401, 'unauthorized', 'Sign in'))
    const login = vi.spyOn(api, 'login').mockResolvedValue({ message: 'OTP sent' })
    const verifyOtp = vi.spyOn(api, 'verifyOtp').mockResolvedValue({
      user: { username: 'owner', role: 'master' },
      message: 'Login successful',
    })

    render(<App />)
    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'owner' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'safe-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    await screen.findByRole('heading', { name: 'Enter your OTP' })
    expect(login).toHaveBeenCalledWith('owner', 'safe-password')

    fireEvent.change(screen.getByLabelText('6-digit code'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await screen.findByRole('button', { name: /Payslip/ })

    expect(verifyOtp).toHaveBeenCalledWith('owner', '123456')
    expect(screen.getByText('owner · master')).toBeInTheDocument()
    for (const moduleName of ['Payslip', 'Bills', 'Inventory', 'Employees', 'Company']) {
      expect(screen.getByRole('button', { name: new RegExp(moduleName) })).toBeInTheDocument()
    }
    expect(screen.getAllByRole('button')).toHaveLength(6)
  })

  it('shows login failures and keeps the form usable', async () => {
    vi.spyOn(api, 'login').mockRejectedValue(
      new ApiError(401, 'invalid_credentials', 'Invalid username or password'),
    )
    const onOtpRequired = vi.fn()
    render(<LoginView onOtpRequired={onOtpRequired} />)
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'owner' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByText('Invalid username or password')).toBeInTheDocument()
    expect(onOtpRequired).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled()
  })

  it('shows OTP errors and requires a six-digit value', async () => {
    const verifyOtp = vi
      .spyOn(api, 'verifyOtp')
      .mockRejectedValue(new ApiError(401, 'invalid_otp', 'Invalid code'))
    const onVerified = vi.fn()
    render(<OtpView username="owner" onVerified={onVerified} />)
    const input = screen.getByLabelText('6-digit code')
    const verifyButton = screen.getByRole('button', { name: 'Verify' })
    expect(verifyButton).toBeDisabled()

    fireEvent.change(input, { target: { value: '123456' } })
    expect(verifyButton).toBeEnabled()
    fireEvent.click(verifyButton)

    expect(await screen.findByText('Invalid code')).toBeInTheDocument()
    expect(verifyOtp).toHaveBeenCalledWith('owner', '123456')
    expect(onVerified).not.toHaveBeenCalled()
  })
})

it('echoes the CSRF cookie on authenticated mutations', async () => {
  document.cookie = 'csrf_token=csrf%20value; path=/'
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: 'Logged out' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)

  await api.logout()

  await waitFor(() => expect(fetchMock).toHaveBeenCalled())
  const [, request] = fetchMock.mock.calls[0] as [string, RequestInit]
  expect(request.headers).toMatchObject({ 'x-csrf-token': 'csrf value' })
})
