import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  createStockCountRequest,
  createWasteRequest,
  listBalancesRequest,
  listIngredientsRequest,
  listLocationsRequest,
  listMovementsRequest,
} from '@/lib/api'

export const InventoryPage = () => {
  const { i18n } = useTranslation()
  const language = i18n.language.startsWith('ar') ? 'ar' : 'en'
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'balances' | 'ledger' | 'waste' | 'count'>('balances')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [wasteForm, setWasteForm] = useState({
    ingredient_id: '',
    location_id: '',
    quantity_base: '',
    reason: '',
  })
  const [countForm, setCountForm] = useState({
    location_id: '',
    ingredient_id: '',
    actual_qty: '',
    notes: '',
  })

  const ingredientsQuery = useQuery({
    queryKey: ['ingredients'],
    queryFn: listIngredientsRequest,
  })
  const locationsQuery = useQuery({ queryKey: ['locations'], queryFn: listLocationsRequest })
  const balancesQuery = useQuery({ queryKey: ['balances'], queryFn: listBalancesRequest })
  const movementsQuery = useQuery({ queryKey: ['movements'], queryFn: listMovementsRequest })

  const localName = (item: { name_en: string; name_ar: string }) =>
    language === 'ar' ? item.name_ar : item.name_en

  const ingredientMap = useMemo(() => {
    const map = new Map<string, { name: string; sku: string }>()
    for (const ingredient of ingredientsQuery.data ?? []) {
      map.set(ingredient.id, { name: localName(ingredient), sku: ingredient.sku })
    }
    return map
  }, [ingredientsQuery.data, language])

  const locationMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const location of locationsQuery.data ?? []) {
      map.set(location.id, `${location.code} — ${localName(location)}`)
    }
    return map
  }, [locationsQuery.data, language])

  const refreshInventory = async () => {
    await queryClient.invalidateQueries({ queryKey: ['balances'] })
    await queryClient.invalidateQueries({ queryKey: ['movements'] })
    await queryClient.invalidateQueries({ queryKey: ['dashboard-inventory'] })
  }

  const wasteMutation = useMutation({
    mutationFn: createWasteRequest,
    onSuccess: async () => {
      await refreshInventory()
      setWasteForm({ ingredient_id: '', location_id: '', quantity_base: '', reason: '' })
      setNotice('Waste recorded')
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const countMutation = useMutation({
    mutationFn: createStockCountRequest,
    onSuccess: async (count) => {
      await refreshInventory()
      setCountForm({ location_id: '', ingredient_id: '', actual_qty: '', notes: '' })
      setNotice(`Stock count ${count.status.toLowerCase()} (variance posted)`)
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleWaste = () => {
    if (
      !wasteForm.ingredient_id ||
      !wasteForm.location_id ||
      !wasteForm.reason ||
      Number(wasteForm.quantity_base) <= 0
    ) {
      setError('Ingredient, location, quantity, and reason are required')
      return
    }
    wasteMutation.mutate(wasteForm)
  }

  const handleCount = () => {
    if (
      !countForm.location_id ||
      !countForm.ingredient_id ||
      countForm.actual_qty === '' ||
      Number(countForm.actual_qty) < 0
    ) {
      setError('Location, ingredient, and actual qty are required')
      return
    }
    countMutation.mutate({
      location_id: countForm.location_id,
      notes: countForm.notes || null,
      post: true,
      items: [{ ingredient_id: countForm.ingredient_id, actual_qty: countForm.actual_qty }],
    })
  }

  const tabs = [
    { id: 'balances' as const, label: 'Balances' },
    { id: 'ledger' as const, label: 'Ledger' },
    { id: 'waste' as const, label: 'Waste' },
    { id: 'count' as const, label: 'Stock count' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Inventory</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Balances, append-only ledger, waste, and stock counts with variance posting.
        </p>
      </div>

      {error ? (
        <Card className="border-red-200 bg-red-50 text-sm text-red-700" role="alert">
          {error}
        </Card>
      ) : null}
      {notice ? (
        <Card className="border-teal-200 bg-teal-50 text-sm text-teal-800" role="status">
          {notice}
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Inventory sections">
        {tabs.map((item) => (
          <Button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            aria-pressed={tab === item.id}
            variant={tab === item.id ? 'default' : 'outline'}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {tab === 'balances' ? (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-start text-sm">
            <thead className="text-stone-500">
              <tr className="border-b border-stone-200">
                <th className="py-2 pe-3 font-medium">Ingredient</th>
                <th className="py-2 pe-3 font-medium">Location</th>
                <th className="py-2 font-medium">Qty on hand</th>
              </tr>
            </thead>
            <tbody>
              {(balancesQuery.data ?? []).map((balance) => (
                <tr key={balance.id} className="border-b border-stone-100">
                  <td className="py-2 pe-3">
                    <span className="font-medium">
                      {ingredientMap.get(balance.ingredient_id)?.name ?? balance.ingredient_id}
                    </span>
                    <span className="ms-2 text-xs text-stone-500">
                      {ingredientMap.get(balance.ingredient_id)?.sku}
                    </span>
                  </td>
                  <td className="py-2 pe-3">
                    {locationMap.get(balance.location_id) ?? balance.location_id}
                  </td>
                  <td className="py-2 font-semibold">{Number(balance.qty_on_hand).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}

      {tab === 'ledger' ? (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-start text-sm">
            <thead className="text-stone-500">
              <tr className="border-b border-stone-200">
                <th className="py-2 pe-3 font-medium">When</th>
                <th className="py-2 pe-3 font-medium">Type</th>
                <th className="py-2 pe-3 font-medium">Ingredient</th>
                <th className="py-2 pe-3 font-medium">Qty</th>
                <th className="py-2 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {(movementsQuery.data ?? []).slice(0, 100).map((movement) => (
                <tr key={movement.id} className="border-b border-stone-100">
                  <td className="py-2 pe-3 text-stone-500">
                    {new Date(movement.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pe-3 font-medium">{movement.type}</td>
                  <td className="py-2 pe-3">
                    {ingredientMap.get(movement.ingredient_id)?.name ?? movement.ingredient_id}
                  </td>
                  <td className="py-2 pe-3">{Number(movement.quantity_base).toFixed(3)}</td>
                  <td className="py-2 text-stone-500">{movement.reason ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}

      {tab === 'waste' ? (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Record waste</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={wasteForm.ingredient_id}
              onChange={(event) =>
                setWasteForm((prev) => ({ ...prev, ingredient_id: event.target.value }))
              }
              aria-label="Waste ingredient"
            >
              <option value="">Ingredient</option>
              {(ingredientsQuery.data ?? []).map((ingredient) => (
                <option key={ingredient.id} value={ingredient.id}>
                  {ingredient.sku} — {localName(ingredient)}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={wasteForm.location_id}
              onChange={(event) =>
                setWasteForm((prev) => ({ ...prev, location_id: event.target.value }))
              }
              aria-label="Waste location"
            >
              <option value="">Location</option>
              {(locationsQuery.data ?? []).map((location) => (
                <option key={location.id} value={location.id}>
                  {location.code} — {localName(location)}
                </option>
              ))}
            </select>
            <Input
              type="number"
              min="0"
              step="0.001"
              placeholder="Quantity (base unit)"
              value={wasteForm.quantity_base}
              onChange={(event) =>
                setWasteForm((prev) => ({ ...prev, quantity_base: event.target.value }))
              }
              aria-label="Waste quantity"
            />
            <Input
              placeholder="Reason"
              value={wasteForm.reason}
              onChange={(event) =>
                setWasteForm((prev) => ({ ...prev, reason: event.target.value }))
              }
              aria-label="Waste reason"
            />
          </div>
          <Button onClick={handleWaste} disabled={wasteMutation.isPending}>
            Post waste
          </Button>
        </Card>
      ) : null}

      {tab === 'count' ? (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Stock count</h2>
          <p className="text-sm text-stone-500">
            Enter counted qty and post immediately — variance adjusts the ledger.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={countForm.location_id}
              onChange={(event) =>
                setCountForm((prev) => ({ ...prev, location_id: event.target.value }))
              }
              aria-label="Count location"
            >
              <option value="">Location</option>
              {(locationsQuery.data ?? []).map((location) => (
                <option key={location.id} value={location.id}>
                  {location.code} — {localName(location)}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={countForm.ingredient_id}
              onChange={(event) =>
                setCountForm((prev) => ({ ...prev, ingredient_id: event.target.value }))
              }
              aria-label="Count ingredient"
            >
              <option value="">Ingredient</option>
              {(ingredientsQuery.data ?? []).map((ingredient) => (
                <option key={ingredient.id} value={ingredient.id}>
                  {ingredient.sku} — {localName(ingredient)}
                </option>
              ))}
            </select>
            <Input
              type="number"
              min="0"
              step="0.001"
              placeholder="Actual qty"
              value={countForm.actual_qty}
              onChange={(event) =>
                setCountForm((prev) => ({ ...prev, actual_qty: event.target.value }))
              }
              aria-label="Actual quantity"
            />
            <Input
              placeholder="Notes (optional)"
              value={countForm.notes}
              onChange={(event) =>
                setCountForm((prev) => ({ ...prev, notes: event.target.value }))
              }
              aria-label="Count notes"
            />
          </div>
          <Button onClick={handleCount} disabled={countMutation.isPending}>
            Post count variance
          </Button>
        </Card>
      ) : null}
    </div>
  )
}
