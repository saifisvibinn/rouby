import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  createProductRequest,
  createRecipeRequest,
  createVariantRequest,
  listCategoriesRequest,
  listIngredientsRequest,
  listProductsRequest,
  listUnitsRequest,
  listVariantsRequest,
  recipeCostRequest,
  recipeHistoryRequest,
} from '@/lib/api'

const money = new Intl.NumberFormat('en-EG', {
  style: 'currency',
  currency: 'EGP',
  maximumFractionDigits: 2,
})

type RecipeLine = { ingredient_id: string; quantity: string; unit_id: string }

export const ProductsPage = () => {
  const { i18n } = useTranslation()
  const language = i18n.language.startsWith('ar') ? 'ar' : 'en'
  const queryClient = useQueryClient()
  const [selectedProductId, setSelectedProductId] = useState<string>('')
  const [selectedVariantId, setSelectedVariantId] = useState<string>('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [productForm, setProductForm] = useState({
    sku: '',
    name_en: '',
    name_ar: '',
    category_id: '',
  })
  const [variantForm, setVariantForm] = useState({
    sku: '',
    name_en: '',
    name_ar: '',
    price: '',
  })
  const [recipeLines, setRecipeLines] = useState<RecipeLine[]>([
    { ingredient_id: '', quantity: '', unit_id: '' },
  ])

  const productsQuery = useQuery({ queryKey: ['products'], queryFn: listProductsRequest })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategoriesRequest })
  const variantsQuery = useQuery({
    queryKey: ['variants', selectedProductId],
    queryFn: () => listVariantsRequest(selectedProductId || undefined),
  })
  const ingredientsQuery = useQuery({
    queryKey: ['ingredients'],
    queryFn: listIngredientsRequest,
  })
  const unitsQuery = useQuery({ queryKey: ['units'], queryFn: listUnitsRequest })
  const historyQuery = useQuery({
    queryKey: ['recipe-history', selectedVariantId],
    queryFn: () => recipeHistoryRequest(selectedVariantId),
    enabled: Boolean(selectedVariantId),
  })
  const costQuery = useQuery({
    queryKey: ['recipe-cost', selectedVariantId],
    queryFn: () => recipeCostRequest(selectedVariantId),
    enabled: Boolean(selectedVariantId),
  })

  const localName = (item: { name_en: string; name_ar: string }) =>
    language === 'ar' ? item.name_ar : item.name_en

  const categoryMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const category of categoriesQuery.data ?? []) {
      map.set(category.id, localName(category))
    }
    return map
  }, [categoriesQuery.data, language])

  const ingredientMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const ingredient of ingredientsQuery.data ?? []) {
      map.set(ingredient.id, `${ingredient.sku} — ${localName(ingredient)}`)
    }
    return map
  }, [ingredientsQuery.data, language])

  const unitMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const unit of unitsQuery.data ?? []) {
      map.set(unit.id, unit.code)
    }
    return map
  }, [unitsQuery.data])

  const productVariants = (variantsQuery.data ?? []).filter(
    (variant) => !selectedProductId || variant.product_id === selectedProductId,
  )

  const createProduct = useMutation({
    mutationFn: createProductRequest,
    onSuccess: async (product) => {
      await queryClient.invalidateQueries({ queryKey: ['products'] })
      setSelectedProductId(product.id)
      setProductForm({ sku: '', name_en: '', name_ar: '', category_id: '' })
      setNotice('Product created')
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const createVariant = useMutation({
    mutationFn: createVariantRequest,
    onSuccess: async (variant) => {
      await queryClient.invalidateQueries({ queryKey: ['variants'] })
      setSelectedVariantId(variant.id)
      setVariantForm({ sku: '', name_en: '', name_ar: '', price: '' })
      setNotice('Variant created')
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const createRecipe = useMutation({
    mutationFn: createRecipeRequest,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['recipe-history', selectedVariantId] })
      await queryClient.invalidateQueries({ queryKey: ['recipe-cost', selectedVariantId] })
      setRecipeLines([{ ingredient_id: '', quantity: '', unit_id: '' }])
      setNotice('New recipe version saved')
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleCreateProduct = () => {
    if (!productForm.sku || !productForm.name_en || !productForm.category_id) {
      setError('SKU, English name, and category are required')
      return
    }
    createProduct.mutate({
      sku: productForm.sku,
      name_en: productForm.name_en,
      name_ar: productForm.name_ar || productForm.name_en,
      category_id: productForm.category_id,
    })
  }

  const handleCreateVariant = () => {
    if (!selectedProductId) {
      setError('Select a product first')
      return
    }
    if (!variantForm.sku || !variantForm.name_en || !variantForm.price) {
      setError('Variant SKU, name, and price are required')
      return
    }
    createVariant.mutate({
      product_id: selectedProductId,
      sku: variantForm.sku,
      name_en: variantForm.name_en,
      name_ar: variantForm.name_ar || variantForm.name_en,
      price: variantForm.price,
    })
  }

  const handleSaveRecipe = () => {
    if (!selectedVariantId) {
      setError('Select a variant first')
      return
    }
    const items = recipeLines.filter(
      (line) => line.ingredient_id && line.unit_id && Number(line.quantity) > 0,
    )
    if (items.length === 0) {
      setError('Add at least one recipe line')
      return
    }
    createRecipe.mutate({ variant_id: selectedVariantId, items })
  }

  const price = Number(
    productVariants.find((variant) => variant.id === selectedVariantId)?.price ?? 0,
  )
  const cost = Number(costQuery.data?.theoretical_cost ?? 0)
  const margin = price > 0 ? ((price - cost) / price) * 100 : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Products</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Manage catalog products, variants, and versioned recipes with live theoretical cost.
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
          <h2 className="text-lg font-semibold">Catalog</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-start text-sm">
              <thead className="text-stone-500">
                <tr className="border-b border-stone-200">
                  <th className="py-2 pe-3 font-medium">Product</th>
                  <th className="py-2 pe-3 font-medium">SKU</th>
                  <th className="py-2 font-medium">Category</th>
                </tr>
              </thead>
              <tbody>
                {(productsQuery.data ?? []).map((product) => (
                  <tr
                    key={product.id}
                    className={`cursor-pointer border-b border-stone-100 ${
                      selectedProductId === product.id ? 'bg-teal-50' : 'hover:bg-stone-50'
                    }`}
                    onClick={() => {
                      setSelectedProductId(product.id)
                      setSelectedVariantId('')
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelectedProductId(product.id)
                        setSelectedVariantId('')
                      }
                    }}
                    tabIndex={0}
                    aria-label={`Select ${localName(product)}`}
                  >
                    <td className="py-2 pe-3 font-medium">{localName(product)}</td>
                    <td className="py-2 pe-3 text-stone-500">{product.sku}</td>
                    <td className="py-2 text-stone-500">
                      {categoryMap.get(product.category_id) ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 border-t border-stone-200 pt-4 sm:grid-cols-2">
            <Input
              placeholder="SKU"
              value={productForm.sku}
              onChange={(event) => setProductForm((prev) => ({ ...prev, sku: event.target.value }))}
              aria-label="Product SKU"
            />
            <select
              className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
              value={productForm.category_id}
              onChange={(event) =>
                setProductForm((prev) => ({ ...prev, category_id: event.target.value }))
              }
              aria-label="Category"
            >
              <option value="">Category</option>
              {(categoriesQuery.data ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {localName(category)}
                </option>
              ))}
            </select>
            <Input
              placeholder="Name (EN)"
              value={productForm.name_en}
              onChange={(event) =>
                setProductForm((prev) => ({ ...prev, name_en: event.target.value }))
              }
              aria-label="Product name English"
            />
            <Input
              placeholder="Name (AR)"
              value={productForm.name_ar}
              onChange={(event) =>
                setProductForm((prev) => ({ ...prev, name_ar: event.target.value }))
              }
              aria-label="Product name Arabic"
            />
            <Button onClick={handleCreateProduct} disabled={createProduct.isPending}>
              Add product
            </Button>
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Variants</h2>
          {!selectedProductId ? (
            <p className="text-sm text-stone-500">Select a product to manage variants.</p>
          ) : (
            <>
              <div className="space-y-2">
                {productVariants.map((variant) => (
                  <button
                    key={variant.id}
                    type="button"
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-start text-sm ${
                      selectedVariantId === variant.id
                        ? 'border-teal-600 bg-teal-50'
                        : 'border-stone-200 hover:border-teal-300'
                    }`}
                    onClick={() => setSelectedVariantId(variant.id)}
                    aria-pressed={selectedVariantId === variant.id}
                  >
                    <span>
                      {localName(variant)}{' '}
                      <span className="text-stone-500">({variant.sku})</span>
                    </span>
                    <span className="font-medium">{money.format(Number(variant.price))}</span>
                  </button>
                ))}
              </div>
              <div className="grid gap-3 border-t border-stone-200 pt-4 sm:grid-cols-2">
                <Input
                  placeholder="Variant SKU"
                  value={variantForm.sku}
                  onChange={(event) =>
                    setVariantForm((prev) => ({ ...prev, sku: event.target.value }))
                  }
                  aria-label="Variant SKU"
                />
                <Input
                  placeholder="Price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={variantForm.price}
                  onChange={(event) =>
                    setVariantForm((prev) => ({ ...prev, price: event.target.value }))
                  }
                  aria-label="Variant price"
                />
                <Input
                  placeholder="Name (EN)"
                  value={variantForm.name_en}
                  onChange={(event) =>
                    setVariantForm((prev) => ({ ...prev, name_en: event.target.value }))
                  }
                  aria-label="Variant name English"
                />
                <Input
                  placeholder="Name (AR)"
                  value={variantForm.name_ar}
                  onChange={(event) =>
                    setVariantForm((prev) => ({ ...prev, name_ar: event.target.value }))
                  }
                  aria-label="Variant name Arabic"
                />
                <Button onClick={handleCreateVariant} disabled={createVariant.isPending}>
                  Add variant
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Recipe editor</h2>
            <p className="mt-1 text-sm text-stone-500">
              Saving creates a new version. Older versions stay in history.
            </p>
          </div>
          {selectedVariantId ? (
            <div className="rounded-lg bg-stone-50 px-4 py-3 text-sm">
              <p>
                Cost: <strong>{money.format(cost)}</strong>
              </p>
              <p>
                Price: <strong>{money.format(price)}</strong>
              </p>
              <p>
                Margin: <strong>{margin.toFixed(1)}%</strong>
              </p>
            </div>
          ) : null}
        </div>

        {!selectedVariantId ? (
          <p className="text-sm text-stone-500">Select a variant to edit its recipe.</p>
        ) : (
          <>
            <div className="space-y-3">
              {recipeLines.map((line, index) => (
                <div key={index} className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto]">
                  <select
                    className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
                    value={line.ingredient_id}
                    onChange={(event) =>
                      setRecipeLines((prev) =>
                        prev.map((item, i) =>
                          i === index ? { ...item, ingredient_id: event.target.value } : item,
                        ),
                      )
                    }
                    aria-label={`Ingredient line ${index + 1}`}
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
                    placeholder="Qty"
                    value={line.quantity}
                    onChange={(event) =>
                      setRecipeLines((prev) =>
                        prev.map((item, i) =>
                          i === index ? { ...item, quantity: event.target.value } : item,
                        ),
                      )
                    }
                    aria-label={`Quantity line ${index + 1}`}
                  />
                  <select
                    className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm"
                    value={line.unit_id}
                    onChange={(event) =>
                      setRecipeLines((prev) =>
                        prev.map((item, i) =>
                          i === index ? { ...item, unit_id: event.target.value } : item,
                        ),
                      )
                    }
                    aria-label={`Unit line ${index + 1}`}
                  >
                    <option value="">Unit</option>
                    {(unitsQuery.data ?? []).map((unit) => (
                      <option key={unit.id} value={unit.id}>
                        {unit.code}
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="ghost"
                    onClick={() =>
                      setRecipeLines((prev) => prev.filter((_, i) => i !== index))
                    }
                    aria-label={`Remove line ${index + 1}`}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() =>
                  setRecipeLines((prev) => [
                    ...prev,
                    { ingredient_id: '', quantity: '', unit_id: '' },
                  ])
                }
              >
                Add line
              </Button>
              <Button onClick={handleSaveRecipe} disabled={createRecipe.isPending}>
                Save new recipe version
              </Button>
            </div>

            <div className="border-t border-stone-200 pt-4">
              <h3 className="mb-3 font-medium">Version history</h3>
              {(historyQuery.data ?? []).length === 0 ? (
                <p className="text-sm text-stone-500">No recipe versions yet.</p>
              ) : (
                <ul className="space-y-3">
                  {(historyQuery.data ?? []).map((version) => (
                    <li
                      key={version.id}
                      className="rounded-lg border border-stone-200 px-3 py-2 text-sm"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">
                          v{version.version_number}
                          {version.is_active ? ' (active)' : ''}
                        </span>
                        <span className="text-stone-500">
                          {new Date(version.effective_from).toLocaleString()}
                        </span>
                      </div>
                      <ul className="mt-2 space-y-1 text-stone-600">
                        {version.items.map((item) => (
                          <li key={item.id}>
                            {ingredientMap.get(item.ingredient_id) ?? item.ingredient_id}:{' '}
                            {item.quantity} {unitMap.get(item.unit_id) ?? ''}
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
