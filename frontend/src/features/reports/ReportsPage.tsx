import { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { profitReportRequest, reportCsvRequest, salesReportRequest } from '@/lib/api'

const money = new Intl.NumberFormat('en-EG', {
  style: 'currency',
  currency: 'EGP',
  maximumFractionDigits: 2,
})

const formatMoney = (value?: string) => money.format(Number(value ?? 0))

const todayDate = () => new Date().toISOString().slice(0, 10)

const startOfDayIso = (value: string) => {
  const date = new Date(value)
  date.setHours(0, 0, 0, 0)
  return date.toISOString()
}

const endOfDayIso = (value: string) => {
  const date = new Date(value)
  date.setHours(23, 59, 59, 999)
  return date.toISOString()
}

export const ReportsPage = () => {
  const [fromDate, setFromDate] = useState(todayDate)
  const [toDate, setToDate] = useState(todayDate)
  const [appliedRange, setAppliedRange] = useState(() => ({
    from: startOfDayIso(todayDate()),
    to: endOfDayIso(todayDate()),
  }))

  const salesQuery = useQuery({
    queryKey: ['reports-sales', appliedRange.from, appliedRange.to],
    queryFn: () => salesReportRequest(appliedRange.from, appliedRange.to),
  })
  const profitQuery = useQuery({
    queryKey: ['reports-profit', appliedRange.from, appliedRange.to],
    queryFn: () => profitReportRequest(appliedRange.from, appliedRange.to),
  })

  const handleApplyRange = () => {
    setAppliedRange({
      from: startOfDayIso(fromDate),
      to: endOfDayIso(toDate),
    })
  }

  const handleDownloadCsv = useCallback(
    async (report: 'sales' | 'profit') => {
      const csv = await reportCsvRequest(report, appliedRange.from, appliedRange.to)
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${report}-report.csv`
      link.click()
      URL.revokeObjectURL(url)
    },
    [appliedRange],
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Reports</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Review sales, payment mix, COGS, gross profit, and margin outliers.
        </p>
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
          <label className="space-y-2 text-sm font-medium text-stone-700">
            From
            <Input
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
              aria-label="Report start date"
            />
          </label>
          <label className="space-y-2 text-sm font-medium text-stone-700">
            To
            <Input
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
              aria-label="Report end date"
            />
          </label>
          <div className="flex items-end">
            <Button onClick={handleApplyRange}>Apply</Button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Sales" value={formatMoney(salesQuery.data?.totals.sales_total)} />
        <SummaryCard label="Orders" value={String(salesQuery.data?.totals.order_count ?? 0)} />
        <SummaryCard label="Avg ticket" value={formatMoney(salesQuery.data?.totals.avg_ticket)} />
        <SummaryCard label="Gross profit" value={formatMoney(profitQuery.data?.totals.gross_profit)} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <ReportHeader title="Sales by category" onDownloadCsv={() => handleDownloadCsv('sales')} />
          <SimpleTable
            columns={['Category', 'Qty', 'Sales']}
            rows={
              salesQuery.data?.by_category.map((row) => [
                row.category,
                String(row.quantity),
                formatMoney(row.sales_total),
              ]) ?? []
            }
          />
        </Card>

        <Card>
          <ReportHeader title="Sales by product" onDownloadCsv={() => handleDownloadCsv('sales')} />
          <SimpleTable
            columns={['Product', 'Qty', 'Sales']}
            rows={
              salesQuery.data?.by_product.map((row) => [
                row.product,
                String(row.quantity),
                formatMoney(row.sales_total),
              ]) ?? []
            }
          />
        </Card>

        <Card>
          <ReportHeader title="Payments" onDownloadCsv={() => handleDownloadCsv('sales')} />
          <SimpleTable
            columns={['Method', 'Total']}
            rows={
              salesQuery.data?.by_payment.map((row) => [
                row.method,
                formatMoney(row.payment_total),
              ]) ?? []
            }
          />
        </Card>

        <Card>
          <ReportHeader title="Profit by product" onDownloadCsv={() => handleDownloadCsv('profit')} />
          <SimpleTable
            columns={['Product', 'Revenue', 'COGS', 'Margin']}
            rows={
              profitQuery.data?.by_product.map((row) => [
                row.product,
                formatMoney(row.revenue),
                formatMoney(row.cogs),
                `${row.margin_percent}%`,
              ]) ?? []
            }
          />
        </Card>

        <Card className="xl:col-span-2">
          <ReportHeader title="High sales, low margin" onDownloadCsv={() => handleDownloadCsv('profit')} />
          <SimpleTable
            columns={['Product', 'Revenue', 'Gross profit', 'Margin']}
            rows={
              profitQuery.data?.high_sales_low_margin.map((row) => [
                row.product,
                formatMoney(row.revenue),
                formatMoney(row.gross_profit),
                `${row.margin_percent}%`,
              ]) ?? []
            }
          />
        </Card>
      </div>
    </div>
  )
}

const SummaryCard = ({ label, value }: { label: string; value: string }) => (
  <Card>
    <p className="text-sm font-medium text-stone-500">{label}</p>
    <p className="mt-2 text-2xl font-semibold text-stone-950">{value}</p>
  </Card>
)

const ReportHeader = ({
  title,
  onDownloadCsv,
}: {
  title: string
  onDownloadCsv: () => void
}) => (
  <div className="mb-4 flex items-center justify-between gap-3">
    <h2 className="text-lg font-semibold text-stone-950">{title}</h2>
    <Button variant="outline" size="sm" onClick={onDownloadCsv}>
      CSV
    </Button>
  </div>
)

const SimpleTable = ({ columns, rows }: { columns: string[]; rows: string[][] }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-stone-200 text-left text-stone-500">
          {columns.map((column) => (
            <th key={column} className="py-2 font-medium">
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={`${row[0]}-${rowIndex}`} className="border-b border-stone-100">
            {row.map((cell, cellIndex) => (
              <td key={`${cell}-${cellIndex}`} className="py-3 text-stone-700">
                {cell}
              </td>
            ))}
          </tr>
        ))}
        {!rows.length && (
          <tr>
            <td className="py-3 text-stone-500" colSpan={columns.length}>
              No report data for this range.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  </div>
)
