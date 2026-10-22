import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { DataTable } from './components/DataTable'
import { KpiCard, KpiRow } from './components/KpiCard'

afterEach(() => {
  cleanup()
})

interface Row {
  id: string
  name: string
  amount: string
}

const ROWS: Row[] = [
  { id: 'r1', name: 'Asha Nair', amount: '1200.50' },
  { id: 'r2', name: 'Bala Menon', amount: '980.00' },
  { id: 'r3', name: 'Cara Das', amount: '1500.25' },
]

const COLUMNS = [
  { key: 'name', header: 'Name' },
  { key: 'amount', header: 'Amount' },
]

const rowKey = (row: Row) => row.id

describe('KpiCard', () => {
  it('shows the label, the value and the hint', () => {
    render(<KpiCard label="Gross payroll" value="6250.35" hint="March 2026" />)
    expect(screen.getByText('Gross payroll')).toBeInTheDocument()
    expect(screen.getByText('6250.35')).toBeInTheDocument()
    expect(screen.getByText('March 2026')).toBeInTheDocument()
  })

  it('renders the amount as the string it was given', () => {
    render(<KpiCard label="Net" value="4800.10" />)
    // Money arrives as a string from the API (R-05); it must not be
    // reformatted into a float.
    expect(screen.getByText('4800.10')).toBeInTheDocument()
  })

  it('lays a row of cards out', () => {
    render(
      <KpiRow>
        <KpiCard label="One" value="1.00" />
        <KpiCard label="Two" value="2.00" />
      </KpiRow>,
    )
    expect(screen.getByText('One')).toBeInTheDocument()
    expect(screen.getByText('Two')).toBeInTheDocument()
  })
})

describe('DataTable', () => {
  it('lists the rows', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} rowKey={rowKey} />)
    expect(screen.getByText('Asha Nair')).toBeInTheDocument()
    expect(screen.getByText('1200.50')).toBeInTheDocument()
    expect(screen.getByText('3 rows')).toBeInTheDocument()
  })

  it('filters the rows', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} rowKey={rowKey} />)
    fireEvent.change(screen.getByLabelText('Filter rows'), { target: { value: 'bala' } })
    expect(screen.getByText('Bala Menon')).toBeInTheDocument()
    expect(screen.queryByText('Asha Nair')).not.toBeInTheDocument()
    expect(screen.getByText('1 row (filtered from 3)')).toBeInTheDocument()
  })

  it('sorts on a column header and reverses on a second click', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} rowKey={rowKey} />)
    fireEvent.click(screen.getByRole('button', { name: /Name/ }))
    const names = screen.getAllByRole('row').slice(1).map((row) => row.textContent)
    expect(names[0]).toContain('Asha Nair')
    expect(names[2]).toContain('Cara Das')

    fireEvent.click(screen.getByRole('button', { name: /Name/ }))
    const reversed = screen.getAllByRole('row').slice(1).map((row) => row.textContent)
    expect(reversed[0]).toContain('Cara Das')
  })

  it('paginates', () => {
    const many = Array.from({ length: 12 }, (_, index) => ({
      id: `r${index}`,
      name: `Person ${index}`,
      amount: `${index}.00`,
    }))
    render(<DataTable columns={COLUMNS} rows={many} rowKey={rowKey} pageSize={5} />)
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByText('Person 0')).toBeInTheDocument()
    expect(screen.queryByText('Person 6')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
    expect(screen.getByText('Person 5')).toBeInTheDocument()
  })

  it('selects rows and reports the selection', () => {
    const selected: string[][] = []
    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        rowKey={rowKey}
        selectable
        onSelectionChange={(keys) => selected.push(keys)}
      />,
    )
    fireEvent.click(screen.getByLabelText('Select row r1'))
    expect(screen.getByText('1 selected')).toBeInTheDocument()
    expect(selected[selected.length - 1]).toEqual(['r1'])

    fireEvent.click(screen.getByLabelText('Select all rows on this page'))
    expect(screen.getByText('3 selected')).toBeInTheDocument()
    expect(selected[selected.length - 1]).toEqual(['r1', 'r2', 'r3'])
  })

  it('shows the empty message when there is nothing to list', () => {
    render(
      <DataTable
        columns={COLUMNS}
        rows={[]}
        rowKey={rowKey}
        emptyMessage="No payslips yet."
      />,
    )
    expect(screen.getByText('No payslips yet.')).toBeInTheDocument()
  })
})
