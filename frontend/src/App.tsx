import { BrowserRouter, Route, Routes } from 'react-router-dom'

const MODULES = [
  { name: 'Payslip', icon: '📋', color: 'bg-blue-100 text-blue-700' },
  { name: 'Bills', icon: '🧾', color: 'bg-green-100 text-green-700' },
  { name: 'Inventory', icon: '📦', color: 'bg-amber-100 text-amber-700' },
  { name: 'Employees', icon: '👥', color: 'bg-purple-100 text-purple-700' },
  { name: 'Company', icon: '🏢', color: 'bg-rose-100 text-rose-700' },
]

function Landing() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 p-8 max-w-4xl">
        {MODULES.map((m) => (
          <div
            key={m.name}
            className="rounded-xl border bg-white p-6 shadow-sm hover:shadow-md transition flex flex-col items-center gap-3 cursor-pointer"
          >
            <div className={`h-12 w-12 rounded-full ${m.color} flex items-center justify-center text-xl`}>
              {m.icon}
            </div>
            <span className="font-semibold text-gray-800">{m.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='*' element={<Landing />} />
      </Routes>
    </BrowserRouter>
  )
}