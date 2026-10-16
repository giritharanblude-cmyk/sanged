import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api, ApiError } from './api'
import { CreatePayslip } from './views/CreatePayslip'
import { PayslipView } from './views/PayslipView'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('payslip screens', () => {
  it('validates entry fields and submits a real API payload', async () => {
    const create = vi.spyOn(api, 'createPayslip').mockResolvedValue({
      id: 'payslip-1',
      employee_code: 'EMP-42',
      month: '2026-01',
      status: 'draft',
      gross: 5000,
      total_deductions: 250,
      net: 4750,
      net_in_words: 'Four Thousand Seven Hundred Fifty Only',
    })
    const onCreated = vi.fn()
    render(<CreatePayslip onCreated={onCreated} />)

    fireEvent.change(screen.getByLabelText('Employee code'), { target: { value: 'EMP-42' } })
    fireEvent.change(screen.getByLabelText('Employee name'), { target: { value: 'Asha Nair' } })
    fireEvent.change(screen.getByLabelText('Month (YYYY-MM)'), { target: { value: '2026-01' } })
    fireEvent.change(screen.getByLabelText('Basic'), { target: { value: '5000' } })
    fireEvent.change(screen.getByLabelText('Other allowances'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Deduction amount'), { target: { value: '250' } })
    fireEvent.change(screen.getByLabelText('Working days'), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText('Days paid'), { target: { value: '31' } })
    expect((screen.getByLabelText('Days paid') as HTMLInputElement).validity.valid).toBe(false)

    fireEvent.change(screen.getByLabelText('Days paid'), { target: { value: '28' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create payslip' }))

    expect(create).toHaveBeenCalledWith({
      employee_code: 'EMP-42',
      employee_name: 'Asha Nair',
      month: '2026-01',
      basic: 5000,
      other_allowances: 0,
      total_working_days: 30,
      days_paid: 28,
      deduction_lines: [{ kind: 'deduction', label: 'PF', amount: 250 }],
    })
    await waitFor(() => expect(onCreated).toHaveBeenCalled())
  })

  it('shows API errors without hiding the payslip form', async () => {
    vi.spyOn(api, 'createPayslip').mockRejectedValue(
      new ApiError(422, 'validation_error', 'Days paid exceeds working days'),
    )
    render(<CreatePayslip onCreated={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Employee code'), { target: { value: 'EMP-42' } })
    fireEvent.change(screen.getByLabelText('Month (YYYY-MM)'), { target: { value: '2026-01' } })
    fireEvent.change(screen.getByLabelText('Basic'), { target: { value: '5000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create payslip' }))

    expect(await screen.findByText('Days paid exceeds working days')).toBeInTheDocument()
    expect(screen.getByLabelText('Employee code')).toBeInTheDocument()
  })

  it('shows list loading completion, empty state, and API failure', async () => {
    vi.spyOn(api, 'listPayslips').mockResolvedValue([])
    const { unmount } = render(
      <PayslipView username="owner" role="master" onLogout={vi.fn()} />,
    )
    expect(await screen.findByText(/No payslips yet/)).toBeInTheDocument()
    unmount()

    vi.spyOn(api, 'listPayslips').mockRejectedValue(new Error('network down'))
    render(<PayslipView username="owner" role="master" onLogout={vi.fn()} />)
    expect(await screen.findByText('Could not load payslips')).toBeInTheDocument()
  })

  it('renders payslip rows, toggles the form, and logs out', async () => {
    vi.spyOn(api, 'listPayslips').mockResolvedValue([
      {
        id: 'payslip-1',
        employee_code: 'EMP-42',
        month: '2026-01',
        status: 'draft',
        gross: 5000,
        total_deductions: 250,
        net: 4750,
        net_in_words: 'Four Thousand Seven Hundred Fifty Only',
      },
    ])
    vi.spyOn(api, 'logout').mockResolvedValue({ message: 'Logged out' })
    const onLogout = vi.fn()
    render(<PayslipView username="owner" role="master" onLogout={onLogout} />)

    expect(await screen.findByText('EMP-42')).toBeInTheDocument()
    expect(screen.getByText('4750.00')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'New payslip' }))
    expect(screen.getByLabelText('Employee code')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Employee code')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    await waitFor(() => expect(onLogout).toHaveBeenCalledOnce())
  })
})
