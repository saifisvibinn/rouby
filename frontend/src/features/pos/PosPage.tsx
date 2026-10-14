import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  addSalePaymentRequest,
  confirmSaleRequest,
  createSaleRequest,
  getPosMenuRequest,
  updateSaleStatusRequest,
  type PosCategory,
  type PosModifier,
  type PosProduct,
  type PosVariant,
  type SaleOut,
} from '@/lib/api'
import { cn } from '@/lib/utils'

type CartItem = {
  key: string
  product: PosProduct
  variant: PosVariant
  modifiers: PosModifier[]
  qty: number
  notes: string
}

type PaymentMethod = 'cash' | 'card' | 'wallet' | 'split'
type OrderType = 'dine_in' | 'takeaway'

const moneyFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const toNumber = (value: string | number | null | undefined) => Number(value ?? 0)

const formatMoney = (value: string | number) => moneyFormatter.format(toNumber(value))

const buildCartKey = (variantId: string, modifierIds: string[], notes: string) =>
  [variantId, [...modifierIds].sort().join(','), notes.trim()].join('|')

const statusFlow = ['CONFIRMED', 'PREPARING', 'COMPLETED']

export const PosPage = () => {
  const { t, i18n } = useTranslation()
  const language = i18n.language.startsWith('ar') ? 'ar' : 'en'
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null)
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [selectedProduct, setSelectedProduct] = useState<PosProduct | null>(null)
  const [selectedVariantId, setSelectedVariantId] = useState('')
  const [selectedModifierIds, setSelectedModifierIds] = useState<string[]>([])
  const [lineNotes, setLineNotes] = useState('')
  const [orderType, setOrderType] = useState<OrderType>('dine_in')
  const [discount, setDiscount] = useState('0')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash')
  const [cashAmount, setCashAmount] = useState('')
  const [cardAmount, setCardAmount] = useState('')
  const [walletAmount, setWalletAmount] = useState('')
  const [openOrders, setOpenOrders] = useState<SaleOut[]>([])
  const [receiptSale, setReceiptSale] = useState<SaleOut | null>(null)
  const [receiptItems, setReceiptItems] = useState<CartItem[]>([])
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isConfirming, setIsConfirming] = useState(false)

  const menuQuery = useQuery({
    queryKey: ['pos-menu'],
    queryFn: getPosMenuRequest,
  })

  const categories = menuQuery.data ?? []

  useEffect(() => {
    if (!activeCategoryId && categories[0]) {
      setActiveCategoryId(categories[0].id)
    }
  }, [activeCategoryId, categories])

  const activeCategory = useMemo(
    () => categories.find((category) => category.id === activeCategoryId) ?? categories[0],
    [activeCategoryId, categories],
  )

  const localName = (item: { name_en: string; name_ar: string }) =>
    language === 'ar' ? item.name_ar : item.name_en

  const availableVariant = (product: PosProduct) =>
    product.variants.find((variant) => variant.available) ?? product.variants[0]

  const hasAvailableVariant = (product: PosProduct) =>
    product.variants.some((variant) => variant.available)

  const cartSubtotal = useMemo(
    () =>
      cartItems.reduce((sum, item) => {
        const modifierTotal = item.modifiers.reduce(
          (modSum, modifier) => modSum + toNumber(modifier.price_delta),
          0,
        )
        return sum + (toNumber(item.variant.price) + modifierTotal) * item.qty
      }, 0),
    [cartItems],
  )

  const discountValue = Math.max(0, toNumber(discount))
  const taxAmount = 0
  const cartTotal = Math.max(0, cartSubtotal - discountValue + taxAmount)
  const paidTotal =
    paymentMethod === 'split'
      ? toNumber(cashAmount) + toNumber(cardAmount) + toNumber(walletAmount)
      : toNumber(
          paymentMethod === 'cash'
            ? cashAmount
            : paymentMethod === 'card'
              ? cardAmount
              : walletAmount,
        )
  const changeDue = paymentMethod === 'cash' ? Math.max(0, paidTotal - cartTotal) : 0
  const balanceDue = Math.max(0, cartTotal - paidTotal)
  const canConfirm = cartItems.length > 0 && paidTotal >= cartTotal && !isConfirming

  const handleProductClick = (product: PosProduct) => {
    const variant = availableVariant(product)
    if (!variant?.available) return

    setError(null)
    setNotice(null)
    setSelectedVariantId(variant.id)
    setSelectedModifierIds([])
    setLineNotes('')

    if (product.variants.length === 1 && product.modifier_groups.length === 0) {
      handleAddConfiguredItem(product, variant, [], '')
      return
    }

    setSelectedProduct(product)
  }

  const handleAddConfiguredItem = (
    product: PosProduct,
    variant: PosVariant,
    modifiers: PosModifier[],
    notes: string,
  ) => {
    const key = buildCartKey(
      variant.id,
      modifiers.map((modifier) => modifier.id),
      notes,
    )
    setCartItems((items) => {
      const existing = items.find((item) => item.key === key)
      if (existing) {
        return items.map((item) => (item.key === key ? { ...item, qty: item.qty + 1 } : item))
      }
      return [...items, { key, product, variant, modifiers, qty: 1, notes }]
    })
  }

  const handleDialogAdd = () => {
    if (!selectedProduct) return

    const variant = selectedProduct.variants.find((item) => item.id === selectedVariantId)
    if (!variant?.available) return

    const modifiers = selectedProduct.modifier_groups
      .flatMap((group) => group.modifiers)
      .filter((modifier) => selectedModifierIds.includes(modifier.id))

    handleAddConfiguredItem(selectedProduct, variant, modifiers, lineNotes)
    setSelectedProduct(null)
  }

  const handleToggleModifier = (modifier: PosModifier, maxSelect: number) => {
    setSelectedModifierIds((ids) => {
      if (ids.includes(modifier.id)) {
        return ids.filter((id) => id !== modifier.id)
      }
      if (ids.length >= maxSelect && maxSelect > 0) {
        return ids
      }
      return [...ids, modifier.id]
    })
  }

  const handleQtyChange = (key: string, nextQty: number) => {
    setCartItems((items) =>
      items
        .map((item) => (item.key === key ? { ...item, qty: nextQty } : item))
        .filter((item) => item.qty > 0),
    )
  }

  const handlePaymentMethodChange = (method: PaymentMethod) => {
    setPaymentMethod(method)
    setCashAmount(method === 'cash' || method === 'split' ? cartTotal.toFixed(2) : '')
    setCardAmount(method === 'card' ? cartTotal.toFixed(2) : '')
    setWalletAmount(method === 'wallet' ? cartTotal.toFixed(2) : '')
  }

  const paymentLines = () => {
    if (paymentMethod === 'split') {
      return [
        { method: 'cash', amount: cashAmount },
        { method: 'card', amount: cardAmount },
        { method: 'wallet', amount: walletAmount },
      ].filter((line) => toNumber(line.amount) > 0)
    }

    return [
      {
        method: paymentMethod,
        amount:
          paymentMethod === 'cash'
            ? cashAmount
            : paymentMethod === 'card'
              ? cardAmount
              : walletAmount,
      },
    ]
  }

  const handleConfirm = async () => {
    if (!canConfirm) return

    setIsConfirming(true)
    setError(null)
    setNotice(null)
    try {
      const sale = await createSaleRequest({
        order_type: orderType,
        discount: discountValue.toFixed(2),
        items: cartItems.map((item) => ({
          variant_id: item.variant.id,
          qty: item.qty,
          modifier_ids: item.modifiers.map((modifier) => modifier.id),
          notes: item.notes || null,
        })),
      })

      for (const line of paymentLines()) {
        await addSalePaymentRequest(sale.id, line.method, toNumber(line.amount).toFixed(2))
      }

      const confirmed = await confirmSaleRequest(sale.id, crypto.randomUUID())
      setReceiptSale(confirmed)
      setReceiptItems(cartItems)
      setOpenOrders((orders) => [confirmed, ...orders])
      setCartItems([])
      setDiscount('0')
      setCashAmount('')
      setCardAmount('')
      setWalletAmount('')
      setNotice(t('pos.saleConfirmed'))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('pos.confirmFailed'))
    } finally {
      setIsConfirming(false)
    }
  }

  const handleStatusChange = async (sale: SaleOut, status: string) => {
    setError(null)
    try {
      const updated = await updateSaleStatusRequest(sale.id, status)
      setOpenOrders((orders) =>
        orders.map((order) => (order.id === updated.id ? updated : order)),
      )
      setReceiptSale((current) => (current?.id === updated.id ? updated : current))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('pos.statusFailed'))
    }
  }

  const renderMoneyLine = (label: string, value: number | string, className?: string) => (
    <div className={cn('flex justify-between text-sm', className)}>
      <span>{label}</span>
      <span>{formatMoney(value)}</span>
    </div>
  )

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-teal-700">
            {t('nav.pos')}
          </p>
          <h1 className="text-2xl font-semibold text-stone-950 sm:text-3xl">{t('pos.title')}</h1>
        </div>
        <div className="flex w-full rounded-xl border border-stone-200 bg-white p-1 sm:w-auto">
          {(['dine_in', 'takeaway'] as OrderType[]).map((type) => (
            <Button
              key={type}
              className="min-h-11 flex-1 sm:flex-none"
              variant={orderType === type ? 'default' : 'ghost'}
              onClick={() => setOrderType(type)}
              aria-pressed={orderType === type}
            >
              {t(`pos.${type}`)}
            </Button>
          ))}
        </div>
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

      <div className="grid gap-4 sm:gap-6 xl:grid-cols-[1fr_420px]">
        <section className="order-2 space-y-4 xl:order-1">
          <div
            className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0"
            role="tablist"
            aria-label={t('pos.categories')}
          >
            {categories.map((category: PosCategory) => (
              <Button
                key={category.id}
                role="tab"
                variant={category.id === activeCategory?.id ? 'default' : 'outline'}
                className="min-h-11 shrink-0"
                aria-selected={category.id === activeCategory?.id}
                aria-pressed={category.id === activeCategory?.id}
                onClick={() => setActiveCategoryId(category.id)}
              >
                {localName(category)}
              </Button>
            ))}
          </div>

          {menuQuery.isLoading ? (
            <Card>{t('pos.loadingMenu')}</Card>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {activeCategory?.products.map((product) => {
              const variant = availableVariant(product)
              const available = hasAvailableVariant(product)

              return (
                <button
                  key={product.id}
                  type="button"
                  className={cn(
                    'min-h-32 rounded-xl border bg-white p-4 text-start shadow-sm transition hover:border-teal-300 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700',
                    !available && 'cursor-not-allowed bg-stone-100 text-stone-400 opacity-70',
                  )}
                  onClick={() => handleProductClick(product)}
                  disabled={!available}
                  aria-label={`${localName(product)} ${formatMoney(variant?.price ?? 0)}`}
                >
                  <div className="flex h-full flex-col justify-between gap-4">
                    <div>
                      <p className="text-lg font-semibold">{localName(product)}</p>
                      <p className="mt-1 text-xs uppercase tracking-wide text-stone-500">
                        {product.sku}
                      </p>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xl font-semibold text-teal-800">
                        {formatMoney(variant?.price ?? 0)}
                      </span>
                      {!available ? (
                        <span className="rounded-full bg-stone-200 px-2 py-1 text-xs text-stone-600">
                          {t('pos.unavailable')}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </section>

        <aside className="order-1 space-y-4 xl:order-2" aria-label={t('pos.cart')}>
          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold" id="pos-cart-heading">
                {t('pos.cart')}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCartItems([])}
                aria-label={t('pos.clear')}
              >
                {t('pos.clear')}
              </Button>
            </div>

            {cartItems.length === 0 ? (
              <p className="rounded-lg bg-stone-50 p-4 text-sm text-stone-500">
                {t('pos.emptyCart')}
              </p>
            ) : (
              <div className="space-y-3">
                {cartItems.map((item) => (
                  <div key={item.key} className="rounded-lg border border-stone-200 p-3">
                    <div className="flex justify-between gap-3">
                      <div>
                        <p className="font-medium">{localName(item.product)}</p>
                        <p className="text-xs text-stone-500">{localName(item.variant)}</p>
                        {item.modifiers.length > 0 ? (
                          <p className="mt-1 text-xs text-stone-500">
                            {item.modifiers.map((modifier) => localName(modifier)).join(', ')}
                          </p>
                        ) : null}
                        {item.notes ? (
                          <p className="mt-1 text-xs text-stone-500">
                            {t('pos.notes')}: {item.notes}
                          </p>
                        ) : null}
                      </div>
                      <p className="font-semibold">
                        {formatMoney(
                          (toNumber(item.variant.price) +
                            item.modifiers.reduce(
                              (sum, modifier) => sum + toNumber(modifier.price_delta),
                              0,
                            )) *
                            item.qty,
                        )}
                      </p>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleQtyChange(item.key, item.qty - 1)}
                        aria-label={t('pos.decreaseQty')}
                      >
                        -
                      </Button>
                      <span className="w-8 text-center font-semibold">{item.qty}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleQtyChange(item.key, item.qty + 1)}
                        aria-label={t('pos.increaseQty')}
                      >
                        +
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.discount')}
                <Input
                  type="number"
                  min="0"
                  value={discount}
                  onChange={(event) => setDiscount(event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.tax')}
                <Input value={formatMoney(taxAmount)} readOnly />
              </label>
            </div>

            <div className="space-y-2 border-t border-stone-200 pt-4">
              {renderMoneyLine(t('pos.subtotal'), cartSubtotal)}
              {renderMoneyLine(t('pos.discount'), discountValue)}
              {renderMoneyLine(t('pos.tax'), taxAmount)}
              {renderMoneyLine(t('pos.total'), cartTotal, 'text-lg font-semibold text-stone-950')}
            </div>
          </Card>

          <Card className="space-y-4">
            <h2 className="text-xl font-semibold">{t('pos.payment')}</h2>
            <div className="grid grid-cols-2 gap-2">
              {(['cash', 'card', 'wallet', 'split'] as PaymentMethod[]).map((method) => (
                <Button
                  key={method}
                  variant={paymentMethod === method ? 'default' : 'outline'}
                  onClick={() => handlePaymentMethodChange(method)}
                  aria-pressed={paymentMethod === method}
                >
                  {t(`pos.${method}`)}
                </Button>
              ))}
            </div>

            {(paymentMethod === 'cash' || paymentMethod === 'split') && (
              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.cash')}
                <Input
                  type="number"
                  min="0"
                  value={cashAmount}
                  onChange={(event) => setCashAmount(event.target.value)}
                />
              </label>
            )}
            {(paymentMethod === 'card' || paymentMethod === 'split') && (
              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.card')}
                <Input
                  type="number"
                  min="0"
                  value={cardAmount}
                  onChange={(event) => setCardAmount(event.target.value)}
                />
              </label>
            )}
            {(paymentMethod === 'wallet' || paymentMethod === 'split') && (
              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.wallet')}
                <Input
                  type="number"
                  min="0"
                  value={walletAmount}
                  onChange={(event) => setWalletAmount(event.target.value)}
                />
              </label>
            )}

            <div className="space-y-2 border-t border-stone-200 pt-4">
              {renderMoneyLine(t('pos.paid'), paidTotal)}
              {renderMoneyLine(t('pos.balanceDue'), balanceDue)}
              {renderMoneyLine(t('pos.change'), changeDue)}
            </div>
            <Button
              className="sticky bottom-2 z-10 w-full min-h-12 shadow-lg sm:static sm:shadow-none"
              size="lg"
              onClick={handleConfirm}
              disabled={!canConfirm}
            >
              {isConfirming ? t('pos.confirming') : t('pos.confirm')}
            </Button>
          </Card>
        </aside>
      </div>

      <section className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card className="space-y-4">
          <h2 className="text-xl font-semibold">{t('pos.openOrders')}</h2>
          {openOrders.length === 0 ? (
            <p className="text-sm text-stone-500">{t('pos.noOpenOrders')}</p>
          ) : (
            <div className="space-y-3">
              {openOrders.map((sale) => (
                <div key={sale.id} className="rounded-lg border border-stone-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">
                        #{sale.id.slice(0, 8)} · {formatMoney(sale.total)}
                      </p>
                      <p className="text-xs text-stone-500">
                        {t(`pos.${sale.order_type}`)} · {sale.items.length} {t('pos.items')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {statusFlow.map((status) => (
                        <span
                          key={status}
                          className={cn(
                            'rounded-full border px-3 py-1 text-xs font-medium',
                            sale.status === status
                              ? 'border-teal-700 bg-teal-50 text-teal-800'
                              : 'border-stone-200 bg-stone-50 text-stone-500',
                          )}
                        >
                          {t(`pos.status.${status}`)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange(sale, 'PREPARING')}
                      disabled={sale.status !== 'CONFIRMED'}
                    >
                      {t('pos.markPreparing')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange(sale, 'COMPLETED')}
                      disabled={sale.status === 'COMPLETED' || sale.status === 'CANCELLED'}
                    >
                      {t('pos.markCompleted')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="pos-receipt-print space-y-4">
          <div className="flex items-center justify-between gap-3 print:hidden">
            <h2 className="text-xl font-semibold">{t('pos.receipt')}</h2>
            <Button variant="outline" onClick={() => window.print()} disabled={!receiptSale}>
              {t('pos.print')}
            </Button>
          </div>
          {receiptSale ? (
            <div className="space-y-3 text-sm">
              <div className="text-center">
                <p className="text-lg font-bold">{t('appName')}</p>
                <p>{t('pos.receipt')}</p>
                <p>#{receiptSale.id.slice(0, 8)}</p>
              </div>
              <div className="border-y border-dashed border-stone-300 py-2">
                {receiptSale.items.map((item) => {
                  const cartMatch = receiptItems.find((cartItem) => cartItem.variant.id === item.variant_id)
                  return (
                    <div key={item.id} className="flex justify-between gap-3">
                      <span>
                        {item.qty} x {cartMatch ? localName(cartMatch.product) : item.variant_id.slice(0, 8)}
                      </span>
                      <span>{formatMoney(item.line_total)}</span>
                    </div>
                  )
                })}
              </div>
              {renderMoneyLine(t('pos.subtotal'), receiptSale.subtotal)}
              {renderMoneyLine(t('pos.discount'), receiptSale.discount)}
              {renderMoneyLine(t('pos.tax'), receiptSale.tax)}
              {renderMoneyLine(t('pos.total'), receiptSale.total, 'font-bold')}
              <p className="rounded-lg bg-teal-50 p-3 text-center font-medium text-teal-800 print:bg-white">
                {t('pos.success')}
              </p>
            </div>
          ) : (
            <p className="text-sm text-stone-500">{t('pos.noReceipt')}</p>
          )}
        </Card>
      </section>

      {selectedProduct ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-stone-950/40 p-0 sm:items-center sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-label={t('pos.configureItem')}
        >
          <Card className="max-h-[92dvh] w-full max-w-xl overflow-y-auto rounded-b-none pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:rounded-xl sm:pb-6">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold sm:text-2xl">{localName(selectedProduct)}</h2>
                <p className="text-sm text-stone-500">{t('pos.configureItem')}</p>
              </div>
              <Button
                variant="ghost"
                className="min-h-11 min-w-11"
                onClick={() => setSelectedProduct(null)}
                aria-label={t('pos.close')}
              >
                x
              </Button>
            </div>

            <div className="space-y-5">
              <div className="space-y-2">
                <p className="text-sm font-medium text-stone-700">{t('pos.size')}</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {selectedProduct.variants.map((variant) => (
                    <Button
                      key={variant.id}
                      variant={selectedVariantId === variant.id ? 'default' : 'outline'}
                      className="justify-between"
                      onClick={() => setSelectedVariantId(variant.id)}
                      disabled={!variant.available}
                    >
                      <span>{localName(variant)}</span>
                      <span>{formatMoney(variant.price)}</span>
                    </Button>
                  ))}
                </div>
              </div>

              {selectedProduct.modifier_groups.map((group) => (
                <div key={group.id} className="space-y-2">
                  <p className="text-sm font-medium text-stone-700">
                    {localName(group)}{' '}
                    <span className="text-xs font-normal text-stone-500">
                      {t('pos.chooseUpTo', { count: group.max_select })}
                    </span>
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {group.modifiers.map((modifier) => (
                      <Button
                        key={modifier.id}
                        variant={selectedModifierIds.includes(modifier.id) ? 'default' : 'outline'}
                        className="justify-between"
                        onClick={() => handleToggleModifier(modifier, group.max_select)}
                      >
                        <span>{localName(modifier)}</span>
                        <span>+{formatMoney(modifier.price_delta)}</span>
                      </Button>
                    ))}
                  </div>
                </div>
              ))}

              <label className="space-y-1 text-sm font-medium text-stone-700">
                {t('pos.notes')}
                <Input value={lineNotes} onChange={(event) => setLineNotes(event.target.value)} />
              </label>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setSelectedProduct(null)}>
                  {t('pos.cancel')}
                </Button>
                <Button onClick={handleDialogAdd}>{t('pos.addToCart')}</Button>
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
