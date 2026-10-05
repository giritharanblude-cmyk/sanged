import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, type Payslip } from '../api'
import { CreatePayslip } from './CreatePayslip'

interface Props {
  username: string
  onLogout: () => void
}

export function PayslipView({ username, onLogout }: Props) {
  const [rows, setRows] = useState<Payslip[] | null>(null)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    try {
      setRows(await api.listPayslips())
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load payslips')
      setRows([])
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700">
              📋
            </span>
            <span className="font-semibold text-gray-900">Payslips</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{username}</span>
            <button
              onClick={async () => {
                await api.logout().catch(() => undefined)
                onLogout()
              }}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">All payslips</h2>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            {showForm ? 'Cancel' : 'New payslip'}
          </button>
        </div>

        {showForm && (
          <div className="mb-6 rounded-xl border bg-white p-6 shadow-sm">
            <CreatePayslip
              onCreated={async () => {
                setShowForm(false)
                await load()
              }}
            />
          </div>
        )}

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        {rows === null && <p className="text-sm text-gray-500">Loading…</p>}

        {rows !== null && rows.length === 0 && (
          <p className="rounded-xl border border-dashed bg-white p-8 text-center text-sm text-gray-500">
            No payslips yet. Create one to see it listed here.
          </p>
        )}

        {rows !== null && rows.length > 0 && (
          <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Employee</th>
                  <th className="px-4 py-3 font-medium">Month</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Gross</th>
                  <th className="px-4 py-3 text-right font-medium">Deductions</th>
                  <th className="px-4 py-3 text-right font-medium">Net</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {p.employee_code ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{p.month}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {p.gross.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-red-600">
                      {p.total_deductions.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums">
                      {p.net.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}