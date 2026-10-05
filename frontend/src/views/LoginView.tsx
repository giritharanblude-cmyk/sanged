import { useState } from 'react'
import { api, ApiError } from '../api'

interface Props {
  onOtpRequired: (username: string) => void
}

export function LoginView({ onOtpRequired }: Props) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.login(username, password)
      onOtpRequired(username)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">SANGAD</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to continue</p>

        <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
        />

        <label className="block text-sm font-medium text-gray-700 mt-4 mb-1" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
        />

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="mt-6 w-full rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {busy ? 'Sending OTP…' : 'Continue'}
        </button>
      </form>
    </div>
  )
}