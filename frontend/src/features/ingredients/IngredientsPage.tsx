import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  createIngredientRequest,
  listBalancesRequest,
  listIngredientsRequest,
  listLocationsRequest,
  listUnitsRequest,
} from '@/lib/api'
import { cn } from '@/lib/utils'

const money = new Intl.NumberFormat('en-EG', {
  style: 'currency',
  currency: 'EGP',
  maximumFractionDigits: 4,
})

export const IngredientsPage = () => {
  const { i18n } = useTranslation()
  const language = i18n.language.startsWith('ar') ? 'ar' : 'en'
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [form, setForm] = useState({
    sku: '',
    name_en: '',
    name_ar: '',
    storage_unit_id: '',
    purchase_unit_id: '',
    wac: '0',
    min_stock: '0',
    default_location_id: '',
  })

  const ingredientsQuery = useQuery({
    queryKey: ['ingredients'],
    queryFn: listIngredientsRequest,
  })
  const unitsQuery = useQuery({ queryKey: ['units'], queryFn: listUnitsRequest })
  const balancesQuery = useQuery({ queryKey: ['balances'], queryFn: listBalancesRequest })
  const locationsQuery = useQuery({ queryKey: ['locations'], queryFn: listLocationsRequest })

  const localName = (item: { name_en: string; name_ar: string }) =>
    language === 'ar' ? item.name_ar : item.name_en

  const unitCode = useMemo(() => {
    const map = new Map<string, string>()
    for (const unit of unitsQuery.data ?? []) map.set(unit.id, unit.code)
    return map
  }, [unitsQuery.data])

  const qtyByIngredient = useMemo(() => {
    const map = new Map<string, number>()
    for (const balance of balancesQuery.data ?? []) {
      map.set(
        balance.ingredient_id,
        (map.get(balance.ingredient_id) ?? 0) + Number(balance.qty_on_hand),
      )
    }
    return map
  }, [balancesQuery.data])

  const createIngredient = useMutation({
    mutationFn: createIngredientRequest,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['ingredients'] })
      setForm({
        sku: '',
        name_en: '',
        name_ar: '',
        storage_unit_id: '',
        purchase_unit_id: '',
        wac: '0',
        min_stock: '0',
        default_location_id: '',
      })
      setNotice('Ingredient created')
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleCreate = () => {
    if (!form.sku || !form.name_en || !form.storage_unit_id || !form.purchase_unit_id) {
      setError('SKU, name, and units are required')
      return
    }
    createIngredient.mutate({
      sku: form.sku,
      name_en: form.name_en,
      name_ar: form.name_ar || form.name_en,
      storage_unit_id: form.storage_unit_id,
      purchase_unit_id: form.purchase_unit_id,
      wac: form.wac,
      min_stock: form.min_stock,
      density_g_per_ml: null,
      barcode: null,
      default_supplier_id: null,
      default_location_id: form.default_location_id || null,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Ingredients</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Ingredient master with on-hand stock and low-stock badges.
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

      <Card className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-start text-sm">
          <thead className="text-stone-500">
            <tr className="border-b border-stone-200">
              <th className="py-2 pe-3 font-medium">SKU</th>
              <th className="py-2 pe-3 font-medium">Name</th>
              <th className="py-2 pe-3 font-medium">On hand</th>
              <th className="py-2 pe-3 font-medium">Min</th>
              <th className="py-2 pe-3 font-medium">WAC</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {(ingredientsQuery.data ?? []).map((ingredient) => {
              const onHand = qtyByIngredient.get(ingredient.id) ?? 0
              const minStock = Number(ingredient.min_stock)
              const low = onHand <= minStock
              return (
                <tr key={ingredient.id} className="border-b border-stone-100">
                  <td className="py-2 pe-3 font-mono text-xs">{ingredient.sku}</td>
                  <td className="py-2 pe-3 font-medium">{localName(ingredient)}</td>
                  <td className="py-2 pe-3">
                    {onHand.toFixed(3)} {unitCode.get(ingredient.storage_unit_id) ?? ''}
                  </td>
                  <td className="py-2 pe-3">{minStock.toFixed(3)}</td>
                  <td className="py-2 pe-3">{money.format(Number(ingredient.wac))}</td>
                  <td className="py-2">
                    <span
                      className={cn(
                        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                        low
                          ? 'bg-amber-100 text-amber-900'
                          : 'bg-teal-50 text-teal-800',
                      )}
                    >
                      {low ? 'Low stock' : 'OK'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-lg font-semibold">Add ingredient</h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <Input
            placeholder="SKU"
            value={form.sku}
            onChange={(event) => setForm((prev) => ({ ...prev, sku: event.target.value }))}
            aria-label="Ingredient SKU"
          />
          <Input
            placeholder="Name (EN)"
            value={form.name_en}
            onChange={(event) => setForm((prev) => ({ ...prev, name_en: event.target.value }))}
            aria-label="Ingredient name English"
          />
          <Input
            placeholder="Name (AR)"
            value={form.name_ar}
            onChange={(event) => setForm((prev) => ({ ...prev, name_ar: event.target.value }))}
            aria-label="Ingredient name Arabic"
          />
          <select
            className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
            value={form.storage_unit_id}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, storage_unit_id: event.target.value }))
            }
            aria-label="Storage unit"
          >
            <option value="">Storage unit</option>
            {(unitsQuery.data ?? []).map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.code} — {localName(unit)}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
            value={form.purchase_unit_id}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, purchase_unit_id: event.target.value }))
            }
            aria-label="Purchase unit"
          >
            <option value="">Purchase unit</option>
            {(unitsQuery.data ?? []).map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.code} — {localName(unit)}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
            value={form.default_location_id}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, default_location_id: event.target.value }))
            }
            aria-label="Default location"
          >
            <option value="">Default location (optional)</option>
            {(locationsQuery.data ?? []).map((location) => (
              <option key={location.id} value={location.id}>
                {location.code} — {localName(location)}
              </option>
            ))}
          </select>
          <Input
            type="number"
            min="0"
            step="0.0001"
            placeholder="WAC"
            value={form.wac}
            onChange={(event) => setForm((prev) => ({ ...prev, wac: event.target.value }))}
            aria-label="Weighted average cost"
          />
          <Input
            type="number"
            min="0"
            step="0.001"
            placeholder="Min stock"
            value={form.min_stock}
            onChange={(event) => setForm((prev) => ({ ...prev, min_stock: event.target.value }))}
            aria-label="Minimum stock"
          />
        </div>
        <Button onClick={handleCreate} disabled={createIngredient.isPending}>
          Add ingredient
        </Button>
      </Card>
    </div>
  )
}
