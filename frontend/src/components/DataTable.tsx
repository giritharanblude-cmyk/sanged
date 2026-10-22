import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export interface DataTableColumn<T> {
  /** Stable name of the column, also used as the sort key. */
  key: string
  header: string
  /** Whether the column can be sorted. Defaults to true. */
  sortable?: boolean
  /** The value used when sorting. Defaults to the rendered text. */
  sortValue?: (row: T) => string | number
  /** The cell content. Defaults to the row's value under the column key. */
  render?: (row: T) => ReactNode
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  /** A stable identity for each row. */
  rowKey: (row: T) => string
  /** Show the selection column and the select-all checkbox. */
  selectable?: boolean
  /** Called whenever the selection changes. */
  onSelectionChange?: (keys: string[]) => void
  /** Rows per page. Defaults to 10. */
  pageSize?: number
  /** Placeholder of the filter box. */
  filterPlaceholder?: string
  /** Shown when there is nothing to list. */
  emptyMessage?: string
}

type SortDirection = 'asc' | 'desc'

function defaultRender<T>(row: T, key: string): ReactNode {
  const value = (row as Record<string, unknown>)[key]
  if (value === null || value === undefined) return '—'
  return String(value)
}

/**
 * The shared table for every module (architecture section 4.2).
 *
 * It sorts, filters, selects and paginates. The component holds no
 * domain knowledge: the caller supplies the columns and the rows.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  selectable = false,
  onSelectionChange,
  pageSize = 10,
  filterPlaceholder = 'Filter…',
  emptyMessage = 'Nothing to show yet.',
}: DataTableProps<T>) {
  const [filter, setFilter] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [direction, setDirection] = useState<SortDirection>('asc')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<string[]>([])

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return rows
    return rows.filter((row) =>
      columns.some((column) =>
        String(defaultRender(row, column.key)).toLowerCase().includes(needle),
      ),
    )
  }, [rows, filter, columns])

  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    const column = columns.find((candidate) => candidate.key === sortKey)
    if (!column) return filtered
    const value = (row: T): string | number =>
      column.sortValue ? column.sortValue(row) : String(defaultRender(row, column.key))
    const copy = [...filtered]
    copy.sort((left, right) => {
      const a = value(left)
      const b = value(right)
      if (a === b) return 0
      const order = a < b ? -1 : 1
      return direction === 'asc' ? order : -order
    })
    return copy
  }, [filtered, sortKey, direction, columns])

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize))
  const currentPage = Math.min(page, pageCount - 1)
  const visible = sorted.slice(currentPage * pageSize, currentPage * pageSize + pageSize)

  function toggleSort(key: string) {
    if (sortKey === key) {
      setDirection(direction === 'asc' ? 'desc' : 'asc')
      return
    }
    setSortKey(key)
    setDirection('asc')
  }

  function updateSelection(keys: string[]) {
    setSelected(keys)
    onSelectionChange?.(keys)
  }

  function toggleRow(key: string) {
    updateSelection(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key])
  }

  function toggleAllOnPage() {
    const pageKeys = visible.map(rowKey)
    const allSelected = pageKeys.every((key) => selected.includes(key))
    updateSelection(
      allSelected
        ? selected.filter((key) => !pageKeys.includes(key))
        : [...new Set([...selected, ...pageKeys])],
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <input
          type="search"
          aria-label="Filter rows"
          className="w-full max-w-xs rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          placeholder={filterPlaceholder}
          value={filter}
          onChange={(event) => {
            setFilter(event.target.value)
            setPage(0)
          }}
        />
        {selectable ? (
          <span className="text-sm text-gray-500">{selected.length} selected</span>
        ) : null}
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-gray-500">
            <tr>
              {selectable ? (
                <th scope="col" className="px-4 py-3">
                  <input
                    type="checkbox"
                    aria-label="Select all rows on this page"
                    checked={
                      visible.length > 0 && visible.map(rowKey).every((key) => selected.includes(key))
                    }
                    onChange={toggleAllOnPage}
                  />
                </th>
              ) : null}
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className="px-4 py-3 font-medium"
                  aria-sort={
                    sortKey === column.key
                      ? direction === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  {column.sortable === false ? (
                    column.header
                  ) : (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 hover:text-gray-800"
                      onClick={() => toggleSort(column.key)}
                    >
                      {column.header}
                      <span aria-hidden="true">{sortKey === column.key ? (direction === 'asc' ? '▲' : '▼') : '↕'}</span>
                    </button>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (selectable ? 1 : 0)}
                  className="px-4 py-6 text-center text-gray-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              visible.map((row) => {
                const key = rowKey(row)
                return (
                  <tr key={key} className="border-b last:border-0">
                    {selectable ? (
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          aria-label={`Select row ${key}`}
                          checked={selected.includes(key)}
                          onChange={() => toggleRow(key)}
                        />
                      </td>
                    ) : null}
                    {columns.map((column) => (
                      <td key={column.key} className="px-4 py-3">
                        {column.render ? column.render(row) : defaultRender(row, column.key)}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>
          {sorted.length} row{sorted.length === 1 ? '' : 's'}
          {sorted.length !== rows.length ? ` (filtered from ${rows.length})` : ''}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-gray-300 px-3 py-1 disabled:opacity-40"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            Previous
          </button>
          <span>
            Page {currentPage + 1} of {pageCount}
          </span>
          <button
            type="button"
            className="rounded-lg border border-gray-300 px-3 py-1 disabled:opacity-40"
            disabled={currentPage >= pageCount - 1}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
