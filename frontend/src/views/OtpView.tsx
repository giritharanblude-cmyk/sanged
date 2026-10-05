import { useState } from 'react'
import { api, ApiError } from '../api'

interface Props {
  username: string
  onVerified: (username: string) => void
}

export function OtpView({ username, onVerified }: Props) {
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await api.verifyOtp(username, otp)
      onVerified(res.user.username)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">Enter your OTP</h1>
        <p className="text-sm text-gray-500 mb-6">
          Sent to the address on file for <span className="font-medium">{username}</span>. With
          Mailpit running you can read it at <span className="font-medium">http://127.0.0.1:8025</span>.
        </p>

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="otp">
          6-digit code
        </label>
        <input
          id="otp"
          value={otp}
          onChange={(e) => setOtp(e.target.value)}
          inputMode="numeric"
          maxLength={6}
          required
          autoFocus
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-lg tracking-widest focus:outline-none focus:ring-2 focus:ring-green-500"
        />

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={busy || otp.length !== 6}
          className="mt-6 w-full rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {busy ? 'Verifying…' : 'Verify'}
        </button>
      </form>
    </div>
  )
}