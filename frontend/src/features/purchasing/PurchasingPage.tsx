import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/AuthContext'
import {
  createGoodsReceiptRequest,
  createPurchaseOrderRequest,
  listIngredientsRequest,
  listLocationsRequest,
  listSuppliersRequest,
} from '@/lib/api'

export const PurchasingPage = () => {
  const { i18n } = useTranslation()
  const language = i18n.language.startsWith('ar') ? 'ar' : 'en'
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [poForm, setPoForm] = useState({
    supplier_id: '',
    ingredient_id: '',
    ordered_qty: '',
    unit_cost: '',
    notes: '',
  })
  const [receiptForm, setReceiptForm] = useState({
    location_id: '',
    supplier_id: '',
    ingredient_id: '',
    received_qty: '',
    unit_cost: '',
    expiry_date: '',
    notes: '',
    confirm: true,
  })

  const ingredientsQuery = useQuery({
    queryKey: ['ingredients'],
    queryFn: listIngredientsRequest,
  })
  const locationsQuery = useQuery({ queryKey: ['locations'], queryFn: listLocationsRequest })
  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: listSuppliersRequest })

  const localName = (item: { name_en: string; name_ar: string }) =>
    language === 'ar' ? item.name_ar : item.name_en

  const poMutation = useMutation({
    mutationFn: createPurchaseOrderRequest,
    onSuccess: (order) => {
      setPoForm({
        supplier_id: '',
        ingredient_id: '',
        ordered_qty: '',
        unit_cost: '',
        notes: '',
      })
      setNotice(`Purchase order created (${order.id.slice(0, 8)}…) — stock unchanged until receipt`)
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const receiptMutation = useMutation({
    mutationFn: createGoodsReceiptRequest,
    onSuccess: async (receipt) => {
      await queryClient.invalidateQueries({ queryKey: ['balances'] })
      await queryClient.invalidateQueries({ queryKey: ['movements'] })
      await queryClient.invalidateQueries({ queryKey: ['ingredients'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-inventory'] })
      setReceiptForm({
        location_id: '',
        supplier_id: '',
        ingredient_id: '',
        received_qty: '',
        unit_cost: '',
        expiry_date: '',
        notes: '',
        confirm: true,
      })
      setNotice(`Goods receipt ${receipt.status.toLowerCase()}`)
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleCreatePo = () => {
    if (!user?.branch_id) {
      setError('No branch on user')
      return
    }
    if (!poForm.ingredient_id || Number(poForm.ordered_qty) <= 0 || Number(poForm.unit_cost) < 0) {
      setError('Ingredient, qty, and unit cost are required')
      return
    }
    poMutation.mutate({
      branch_id: user.branch_id,
      supplier_id: poForm.supplier_id || null,
      notes: poForm.notes || null,
      items: [
        {
          ingredient_id: poForm.ingredient_id,
          ordered_qty: poForm.ordered_qty,
          unit_cost: poForm.unit_cost,
        },
      ],
    })
  }

  const handleReceive = () => {
    if (
      !receiptForm.location_id ||
      !receiptForm.ingredient_id ||
      Number(receiptForm.received_qty) <= 0 ||
      Number(receiptForm.unit_cost) < 0
    ) {
      setError('Location, ingredient, qty, and unit cost are required')
      return
    }
    receiptMutation.mutate({
      location_id: receiptForm.location_id,
      supplier_id: receiptForm.supplier_id || null,
      notes: receiptForm.notes || null,
      confirm: receiptForm.confirm,
      items: [
        {
          ingredient_id: receiptForm.ingredient_id,
          received_qty: receiptForm.received_qty,
          unit_cost: receiptForm.unit_cost,
          expiry_date: receiptForm.expiry_date || null,
        },
      ],
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Purchasing</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Purchase orders do not change stock. Confirming a goods receipt updates balances and WAC.
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

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">New purchase order</h2>
          <div className="grid gap-3">
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={poForm.supplier_id}
              onChange={(event) =>
                setPoForm((prev) => ({ ...prev, supplier_id: event.target.value }))
              }
              aria-label="PO supplier"
            >
              <option value="">Supplier (optional)</option>
              {(suppliersQuery.data ?? []).map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {localName(supplier)}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={poForm.ingredient_id}
              onChange={(event) =>
                setPoForm((prev) => ({ ...prev, ingredient_id: event.target.value }))
              }
              aria-label="PO ingredient"
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
              placeholder="Ordered qty (base)"
              value={poForm.ordered_qty}
              onChange={(event) =>
                setPoForm((prev) => ({ ...prev, ordered_qty: event.target.value }))
              }
              aria-label="Ordered quantity"
            />
            <Input
              type="number"
              min="0"
              step="0.0001"
              placeholder="Unit cost"
              value={poForm.unit_cost}
              onChange={(event) =>
                setPoForm((prev) => ({ ...prev, unit_cost: event.target.value }))
              }
              aria-label="PO unit cost"
            />
            <Input
              placeholder="Notes"
              value={poForm.notes}
              onChange={(event) => setPoForm((prev) => ({ ...prev, notes: event.target.value }))}
              aria-label="PO notes"
            />
            <Button onClick={handleCreatePo} disabled={poMutation.isPending}>
              Create PO
            </Button>
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Receive goods</h2>
          <div className="grid gap-3">
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={receiptForm.location_id}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, location_id: event.target.value }))
              }
              aria-label="Receipt location"
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
              value={receiptForm.supplier_id}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, supplier_id: event.target.value }))
              }
              aria-label="Receipt supplier"
            >
              <option value="">Supplier (optional)</option>
              {(suppliersQuery.data ?? []).map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {localName(supplier)}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={receiptForm.ingredient_id}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, ingredient_id: event.target.value }))
              }
              aria-label="Receipt ingredient"
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
              placeholder="Received qty (base)"
              value={receiptForm.received_qty}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, received_qty: event.target.value }))
              }
              aria-label="Received quantity"
            />
            <Input
              type="number"
              min="0"
              step="0.0001"
              placeholder="Unit cost"
              value={receiptForm.unit_cost}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, unit_cost: event.target.value }))
              }
              aria-label="Receipt unit cost"
            />
            <Input
              type="date"
              value={receiptForm.expiry_date}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, expiry_date: event.target.value }))
              }
              aria-label="Expiry date"
            />
            <Input
              placeholder="Notes"
              value={receiptForm.notes}
              onChange={(event) =>
                setReceiptForm((prev) => ({ ...prev, notes: event.target.value }))
              }
              aria-label="Receipt notes"
            />
            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={receiptForm.confirm}
                onChange={(event) =>
                  setReceiptForm((prev) => ({ ...prev, confirm: event.target.checked }))
                }
              />
              Confirm immediately (update stock + WAC)
            </label>
            <Button onClick={handleReceive} disabled={receiptMutation.isPending}>
              Receive goods
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}
