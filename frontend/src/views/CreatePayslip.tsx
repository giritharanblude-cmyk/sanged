import { useState } from 'react'
import { api, ApiError } from '../api'

interface Props {
  onCreated: () => void | Promise<void>
}

const FIELD =
  'w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500'

export function CreatePayslip({ onCreated }: Props) {
  const [employeeCode, setEmployeeCode] = useState('')
  const [employeeName, setEmployeeName] = useState('')
  const [month, setMonth] = useState('')
  const [basic, setBasic] = useState('')
  const [allowances, setAllowances] = useState('0')
  const [deductionLabel, setDeductionLabel] = useState('PF')
  const [deductionAmount, setDeductionAmount] = useState('0')
  const [workingDays, setWorkingDays] = useState('30')
  const [daysPaid, setDaysPaid] = useState('30')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.createPayslip({
        employee_code: employeeCode,
        employee_name: employeeName,
        month,
        basic: Number(basic),
        other_allowances: Number(allowances || 0),
        total_working_days: Number(workingDays),
        days_paid: Number(daysPaid),
        deduction_lines:
          Number(deductionAmount) > 0
            ? [{ kind: 'deduction', label: deductionLabel, amount: Number(deductionAmount) }]
            : [],
      })
      await onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create payslip')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <h3 className="mb-4 text-sm font-semibold text-gray-900">New payslip</h3>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="ec">
            Employee code
          </label>
          <input id="ec" required value={employeeCode} onChange={(e) => setEmployeeCode(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="en">
            Employee name
          </label>
          <input id="en" value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="month">
            Month (YYYY-MM)
          </label>
          <input id="month" required pattern="\d{4}-\d{2}" placeholder="2026-01" value={month} onChange={(e) => setMonth(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="basic">
            Basic
          </label>
          <input id="basic" required type="number" min="0" step="0.01" value={basic} onChange={(e) => setBasic(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="allow">
            Other allowances
          </label>
          <input id="allow" type="number" min="0" step="0.01" value={allowances} onChange={(e) => setAllowances(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="ded">
            Deduction amount
          </label>
          <input id="ded" type="number" min="0" step="0.01" value={deductionAmount} onChange={(e) => setDeductionAmount(e.target.value)} className={FIELD} />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-700" htmlFor="dlabel">
            Deduction label
          </label>
          <input id="dlabel" value={deductionLabel} onChange={(e) => setDeductionLabel(e.target.value)} className={FIELD} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-gray-700" htmlFor="wd">
              Working days
            </label>
            <input id="wd" required type="number" min="1" max="31" value={workingDays} onChange={(e) => setWorkingDays(e.target.value)} className={FIELD} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-700" htmlFor="dp">
              Days paid
            </label>
            <input id="dp" required type="number" min="0" value={daysPaid} onChange={(e) => setDaysPaid(e.target.value)} className={FIELD} />
          </div>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={busy}
        className="mt-6 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
      >
        {busy ? 'Creating…' : 'Create payslip'}
      </button>
    </form>
  )
}