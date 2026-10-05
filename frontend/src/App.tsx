import { useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import { LoginView } from './views/LoginView'
import { OtpView } from './views/OtpView'
import { PayslipView } from './views/PayslipView'

const MODULES = [
  { name: 'Payslip', icon: '📋', color: 'bg-blue-100 text-blue-700', ready: true },
  { name: 'Bills', icon: '🧾', color: 'bg-green-100 text-green-700', ready: false },
  { name: 'Inventory', icon: '📦', color: 'bg-amber-100 text-amber-700', ready: false },
  { name: 'Employees', icon: '👥', color: 'bg-purple-100 text-purple-700', ready: false },
  { name: 'Company', icon: '🏢', color: 'bg-rose-100 text-rose-700', ready: false },
]

function Landing({ username, onLogout }: { username: string; onLogout: () => void }) {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-8 py-4">
          <span className="font-semibold text-gray-900">SANGAD</span>
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

      <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 p-8 sm:grid-cols-2 lg:grid-cols-3">
        {MODULES.map((m) => (
          <button
            key={m.name}
            onClick={() => m.ready && navigate('/payslips')}
            disabled={!m.ready}
            className={`flex flex-col items-center gap-3 rounded-xl border bg-white p-6 shadow-sm transition ${
              m.ready
                ? 'cursor-pointer hover:shadow-md'
                : 'cursor-not-allowed opacity-60'
            }`}
          >
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-full text-xl ${m.color}`}
            >
              {m.icon}
            </div>
            <span className="font-semibold text-gray-800">{m.name}</span>
            {!m.ready && <span className="text-xs text-gray-400">Not implemented yet</span>}
          </button>
        ))}
      </div>
    </div>
  )
}

type Screen =
  | { name: 'loading' }
  | { name: 'anon' }
  | { name: 'otp'; username: string }
  | { name: 'auth'; username: string }

export function App() {
  const [screen, setScreen] = useState<Screen>({ name: 'loading' })

  const refresh = useCallback(async () => {
    try {
      const me = await api.me()
      setScreen({ name: 'auth', username: me.username })
    } catch {
      setScreen({ name: 'anon' })
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <BrowserRouter>
      {screen.name === 'loading' ? (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
          Loading…
        </div>
      ) : screen.name === 'anon' ? (
        <LoginView onOtpRequired={(username) => setScreen({ name: 'otp', username })} />
      ) : screen.name === 'otp' ? (
        <OtpView
          username={screen.username}
          onVerified={(username) => setScreen({ name: 'auth', username })}
        />
      ) : (
        <Authed username={screen.username} onLogout={() => setScreen({ name: 'anon' })} />
      )}
    </BrowserRouter>
  )
}

function Authed({ username, onLogout }: { username: string; onLogout: () => void }) {
  return (
    <Routes>
      <Route path='/payslips' element={<PayslipView username={username} onLogout={onLogout} />} />
      <Route path='*' element={<Landing username={username} onLogout={onLogout} />} />
      <Route path='/index.html' element={<Navigate to="/" replace />} />
    </Routes>
  )
}