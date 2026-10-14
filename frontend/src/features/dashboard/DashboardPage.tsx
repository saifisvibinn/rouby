import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Card } from '@/components/ui/card'
import { useAuth } from '@/features/auth/AuthContext'
import { inventoryReportRequest, profitReportRequest, salesReportRequest } from '@/lib/api'

const money = new Intl.NumberFormat('en-EG', {
  style: 'currency',
  currency: 'EGP',
  maximumFractionDigits: 2,
})

const formatMoney = (value?: string) => money.format(Number(value ?? 0))

const todayRange = () => {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const end = new Date()
  end.setHours(23, 59, 59, 999)
  return {
    from: start.toISOString(),
    to: end.toISOString(),
  }
}

export const DashboardPage = () => {
  const { t } = useTranslation()
  const { user } = useAuth()
  const range = useMemo(todayRange, [])
  const salesQuery = useQuery({
    queryKey: ['dashboard-sales', range.from, range.to],
    queryFn: () => salesReportRequest(range.from, range.to),
  })
  const profitQuery = useQuery({
    queryKey: ['dashboard-profit', range.from, range.to],
    queryFn: () => profitReportRequest(range.from, range.to),
  })
  const inventoryQuery = useQuery({
    queryKey: ['dashboard-inventory'],
    queryFn: inventoryReportRequest,
  })

  const lowStockItems =
    inventoryQuery.data?.valuation.items
      .filter((item) => Number(item.qty_on_hand) <= Number(item.min_stock))
      .slice(0, 6) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">
          {t('dashboard.welcome', { name: user?.full_name ?? '' })}
        </h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Today&apos;s sales, profit, and stock signals at a glance.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <p className="text-sm font-medium text-stone-500">Today&apos;s sales</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950">
            {formatMoney(salesQuery.data?.totals.sales_total)}
          </p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-stone-500">Orders</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950">
            {salesQuery.data?.totals.order_count ?? 0}
          </p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-stone-500">Average ticket</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950">
            {formatMoney(salesQuery.data?.totals.avg_ticket)}
          </p>
        </Card>
        <Card>
          <p className="text-sm font-medium text-stone-500">Gross profit</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950">
            {formatMoney(profitQuery.data?.totals.gross_profit)}
          </p>
        </Card>
      </div>
      <Card>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-stone-950">Low stock</h2>
            <p className="mt-1 text-sm text-stone-500">Ingredients at or below minimum stock.</p>
          </div>
          <p className="text-sm text-stone-500">{user?.email}</p>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="py-2 font-medium">Ingredient</th>
                <th className="py-2 font-medium">On hand</th>
                <th className="py-2 font-medium">Minimum</th>
              </tr>
            </thead>
            <tbody>
              {lowStockItems.map((item) => (
                <tr key={item.ingredient_id} className="border-b border-stone-100">
                  <td className="py-3 font-medium text-stone-900">{item.name}</td>
                  <td className="py-3 text-stone-700">{item.qty_on_hand}</td>
                  <td className="py-3 text-stone-700">{item.min_stock}</td>
                </tr>
              ))}
              {!lowStockItems.length && (
                <tr>
                  <td className="py-3 text-stone-500" colSpan={3}>
                    No low-stock ingredients.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
