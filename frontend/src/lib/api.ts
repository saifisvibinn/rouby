const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

export type UserMe = {
  id: string
  email: string
  full_name: string
  roles: Array<{ code: string; name_en: string; name_ar: string }>
  permissions: string[]
  branch_id: string | null
}

export type PosModifier = {
  id: string
  code: string
  name_en: string
  name_ar: string
  price_delta: string
}

export type PosModifierGroup = {
  id: string
  code: string
  name_en: string
  name_ar: string
  min_select: number
  max_select: number
  modifiers: PosModifier[]
}

export type PosVariant = {
  id: string
  sku: string
  name_en: string
  name_ar: string
  price: string
  available: boolean
}

export type PosProduct = {
  id: string
  sku: string
  name_en: string
  name_ar: string
  image_url: string | null
  modifier_groups: PosModifierGroup[]
  variants: PosVariant[]
}

export type PosCategory = {
  id: string
  code: string
  name_en: string
  name_ar: string
  products: PosProduct[]
}

export type SaleItemIn = {
  variant_id: string
  qty: number
  modifier_ids?: string[]
  notes?: string | null
}

export type SaleCreate = {
  order_type: 'dine_in' | 'takeaway'
  items: SaleItemIn[]
  discount: string
}

export type SaleItemOut = {
  id: string
  variant_id: string
  recipe_version_id: string | null
  qty: number
  unit_price: string
  line_total: string
  notes: string | null
  cogs: string
  modifiers: Array<{ id: string; modifier_id: string; price_delta: string }>
}

export type PaymentOut = {
  id: string
  sale_id: string
  method: string
  amount: string
  created_at: string
}

export type SaleOut = {
  id: string
  status: string
  order_type: string
  branch_id: string
  user_id: string
  subtotal: string
  discount: string
  tax: string
  total: string
  cogs_total: string
  flagged_negative_stock: boolean
  items: SaleItemOut[]
  payments: PaymentOut[]
  created_at: string
  updated_at: string
}

export type ApiError = {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

export type ScannerPairResponse = {
  session_id: string
  device_token: string
  mode: 'CASHIER' | 'RECEIVE' | 'COUNT' | 'WASTE'
  expires_at: string
}

export type ScanEventResponse = {
  event_id: string
  duplicate: boolean
  session_id: string
  mode: ScannerPairResponse['mode']
  sale_id: string | null
  message: string
  resolved: {
    type: 'variant' | 'ingredient' | 'batch'
    id: string
    code: string
    sku: string | null
    name_en: string
    name_ar: string
    price: string | null
    ingredient_id: string | null
    remaining_qty: string | null
  } | null
}

export type SalesReport = {
  totals: {
    sales_total: string
    order_count: number
    avg_ticket: string
  }
  by_category: Array<{
    category_id: string
    category: string
    quantity: number
    sales_total: string
  }>
  by_product: Array<{
    variant_id: string
    product: string
    quantity: number
    sales_total: string
  }>
  by_payment: Array<{
    method: string
    payment_total: string
  }>
}

export type ProfitReport = {
  totals: {
    revenue: string
    cogs: string
    gross_profit: string
    margin_percent: string
  }
  by_product: Array<{
    variant_id: string
    product: string
    revenue: string
    cogs: string
    gross_profit: string
    margin_percent: string
  }>
  by_category: Array<{
    category_id: string
    category: string
    revenue: string
    cogs: string
    gross_profit: string
    margin_percent: string
  }>
  high_sales_low_margin: Array<{
    variant_id: string
    product: string
    revenue: string
    cogs: string
    gross_profit: string
    margin_percent: string
  }>
}

export type InventoryReport = {
  valuation: {
    total_value: string
    items: Array<{
      ingredient_id: string
      sku: string
      name: string
      qty_on_hand: string
      min_stock: string
      unit_cost: string
      value: string
    }>
  }
  movement_summary: Array<{
    type: string
    movement_count: number
    quantity_base: string
    value: string
  }>
}

let accessToken: string | null = null
let refreshToken: string | null = null

export const setTokens = (tokens: TokenResponse | null) => {
  accessToken = tokens?.access_token ?? null
  refreshToken = tokens?.refresh_token ?? null
  if (tokens) {
    sessionStorage.setItem('rouby_refresh', tokens.refresh_token)
  } else {
    sessionStorage.removeItem('rouby_refresh')
  }
}

export const loadRefreshToken = () => {
  refreshToken = sessionStorage.getItem('rouby_refresh')
  return refreshToken
}

export const getAccessToken = () => accessToken

const parseError = async (response: Response): Promise<never> => {
  let message = response.statusText
  try {
    const data = (await response.json()) as ApiError
    message = data.error?.message ?? message
    throw Object.assign(new Error(message), { code: data.error?.code, status: response.status })
  } catch (err) {
    if (err instanceof Error && 'status' in err) throw err
    throw Object.assign(new Error(message), { status: response.status })
  }
}

export const apiFetch = async <T>(
  path: string,
  options: RequestInit = {},
): Promise<T> => {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    await parseError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const apiFetchText = async (
  path: string,
  options: RequestInit = {},
): Promise<string> => {
  const headers = new Headers(options.headers)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    await parseError(response)
  }
  return response.text()
}

export const loginRequest = (email: string, password: string) =>
  apiFetch<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const meRequest = () => apiFetch<UserMe>('/api/v1/auth/me')

const reportRangeQuery = (from?: string, to?: string) => {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const salesReportRequest = (from?: string, to?: string) =>
  apiFetch<SalesReport>(`/api/v1/reports/sales${reportRangeQuery(from, to)}`)

export const profitReportRequest = (from?: string, to?: string) =>
  apiFetch<ProfitReport>(`/api/v1/reports/profit${reportRangeQuery(from, to)}`)

export const inventoryReportRequest = () =>
  apiFetch<InventoryReport>('/api/v1/reports/inventory')

export const reportCsvRequest = (
  report: 'sales' | 'profit',
  from?: string,
  to?: string,
) => {
  const range = reportRangeQuery(from, to)
  const separator = range ? '&' : '?'
  return apiFetchText(`/api/v1/reports/${report}${range}${separator}format=csv`)
}

export const refreshRequest = async () => {
  const token = refreshToken ?? loadRefreshToken()
  if (!token) {
    throw new Error('No refresh token')
  }
  const tokens = await apiFetch<TokenResponse>('/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: token }),
  })
  setTokens(tokens)
  return tokens
}

export const pairScannerRequest = (pairingToken: string) =>
  apiFetch<ScannerPairResponse>('/api/v1/scanner/pair', {
    method: 'POST',
    body: JSON.stringify({ pairing_token: pairingToken }),
  })

export const submitScanEventRequest = (
  deviceToken: string,
  body: { event_id: string; code: string; qty: number },
) =>
  apiFetch<ScanEventResponse>('/api/v1/scan/events', {
    method: 'POST',
    headers: { 'X-Scanner-Device-Token': deviceToken },
    body: JSON.stringify(body),
  })

export const getPosMenuRequest = () => apiFetch<PosCategory[]>('/api/v1/pos/menu')

export const createSaleRequest = (body: SaleCreate) =>
  apiFetch<SaleOut>('/api/v1/sales', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const updateSaleRequest = (saleId: string, body: Partial<SaleCreate>) =>
  apiFetch<SaleOut>(`/api/v1/sales/${saleId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })

export const confirmSaleRequest = (saleId: string, idempotencyKey: string) =>
  apiFetch<SaleOut>(`/api/v1/sales/${saleId}/confirm`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
  })

export const updateSaleStatusRequest = (saleId: string, status: string) =>
  apiFetch<SaleOut>(`/api/v1/sales/${saleId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })

export const cancelSaleRequest = (saleId: string) =>
  apiFetch<SaleOut>(`/api/v1/sales/${saleId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ line_dispositions: [] }),
  })

export const addSalePaymentRequest = (saleId: string, method: string, amount: string) =>
  apiFetch<PaymentOut>(`/api/v1/sales/${saleId}/payments`, {
    method: 'POST',
    body: JSON.stringify({ method, amount }),
  })

export type UnitOut = {
  id: string
  code: string
  name_en: string
  name_ar: string
  dimension: string
  factor_to_base: string
  is_base: boolean
}

export type CategoryOut = {
  id: string
  code: string
  name_en: string
  name_ar: string
  sort_order: number
  is_active: boolean
}

export type SupplierOut = {
  id: string
  code: string
  name_en: string
  name_ar: string
  is_active: boolean
}

export type IngredientOut = {
  id: string
  sku: string
  name_en: string
  name_ar: string
  storage_unit_id: string
  purchase_unit_id: string
  wac: string
  min_stock: string
  density_g_per_ml: string | null
  barcode: string | null
  default_supplier_id: string | null
  default_location_id: string | null
  is_active: boolean
}

export type ProductOut = {
  id: string
  sku: string
  name_en: string
  name_ar: string
  category_id: string
  image_url: string | null
  sort_order: number
  is_active: boolean
}

export type VariantOut = {
  id: string
  product_id: string
  sku: string
  name_en: string
  name_ar: string
  price: string
  barcode: string | null
  is_active: boolean
}

export type RecipeItemOut = {
  id: string
  ingredient_id: string
  quantity: string
  unit_id: string
}

export type RecipeVersionOut = {
  id: string
  variant_id: string
  version_number: number
  effective_from: string
  is_active: boolean
  items: RecipeItemOut[]
}

export type RecipeCostOut = {
  variant_id: string
  theoretical_cost: string
}

export type LocationOut = {
  id: string
  branch_id: string
  code: string
  name_en: string
  name_ar: string
  is_active: boolean
}

export type InventoryBalanceOut = {
  id: string
  ingredient_id: string
  location_id: string
  branch_id: string
  qty_on_hand: string
}

export type StockMovementOut = {
  id: string
  type: string
  ingredient_id: string
  location_id: string
  branch_id: string
  quantity_base: string
  unit_cost: string | null
  reference_type: string | null
  reference_id: string | null
  user_id: string | null
  reason: string | null
  created_at: string
}

export type SettingOut = {
  id: string
  key: string
  value: string
  description: string | null
}

export type GoodsReceiptOut = {
  id: string
  location_id: string
  branch_id: string
  status: string
  confirmed_at: string | null
  items: Array<{
    id: string
    ingredient_id: string
    received_qty: string
    unit_cost: string
    expiry_date: string | null
  }>
}

export type WasteOut = {
  id: string
  ingredient_id: string
  location_id: string
  branch_id: string
  quantity_base: string
  reason: string
  movement_id: string | null
}

export type StockCountOut = {
  id: string
  location_id: string
  branch_id: string
  status: string
  posted_at: string | null
  items: Array<{
    id: string
    ingredient_id: string
    theoretical_qty: string
    actual_qty: string
    variance_qty: string
    movement_id: string | null
  }>
}

export const listUnitsRequest = () => apiFetch<UnitOut[]>('/api/v1/catalog/units')
export const listCategoriesRequest = () =>
  apiFetch<CategoryOut[]>('/api/v1/catalog/categories')
export const listSuppliersRequest = () =>
  apiFetch<SupplierOut[]>('/api/v1/catalog/suppliers')
export const listIngredientsRequest = () =>
  apiFetch<IngredientOut[]>('/api/v1/catalog/ingredients')
export const createIngredientRequest = (body: Omit<IngredientOut, 'id' | 'is_active'>) =>
  apiFetch<IngredientOut>('/api/v1/catalog/ingredients', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const listProductsRequest = () => apiFetch<ProductOut[]>('/api/v1/catalog/products')
export const createProductRequest = (body: {
  sku: string
  name_en: string
  name_ar: string
  category_id: string
  image_url?: string | null
  sort_order?: number
}) =>
  apiFetch<ProductOut>('/api/v1/catalog/products', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const listVariantsRequest = (productId?: string) => {
  const query = productId ? `?product_id=${productId}` : ''
  return apiFetch<VariantOut[]>(`/api/v1/catalog/variants${query}`)
}
export const createVariantRequest = (body: {
  product_id: string
  sku: string
  name_en: string
  name_ar: string
  price: string
  barcode?: string | null
}) =>
  apiFetch<VariantOut>('/api/v1/catalog/variants', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const recipeHistoryRequest = (variantId: string) =>
  apiFetch<RecipeVersionOut[]>(`/api/v1/catalog/recipes/${variantId}/history`)
export const recipeCostRequest = (variantId: string) =>
  apiFetch<RecipeCostOut>(`/api/v1/catalog/recipes/${variantId}/cost`)
export const createRecipeRequest = (body: {
  variant_id: string
  items: Array<{ ingredient_id: string; quantity: string; unit_id: string }>
}) =>
  apiFetch<RecipeVersionOut>('/api/v1/catalog/recipes', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const listLocationsRequest = () => apiFetch<LocationOut[]>('/api/v1/locations')
export const listBalancesRequest = () =>
  apiFetch<InventoryBalanceOut[]>('/api/v1/inventory/balances')
export const listMovementsRequest = () =>
  apiFetch<StockMovementOut[]>('/api/v1/stock-movements')
export const createWasteRequest = (body: {
  ingredient_id: string
  location_id: string
  quantity_base: string
  reason: string
}) =>
  apiFetch<WasteOut>('/api/v1/waste', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const createStockCountRequest = (body: {
  location_id: string
  notes?: string | null
  post?: boolean
  items: Array<{ ingredient_id: string; actual_qty: string }>
}) =>
  apiFetch<StockCountOut>('/api/v1/stock-counts', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const createPurchaseOrderRequest = (body: {
  branch_id: string
  supplier_id?: string | null
  notes?: string | null
  items: Array<{
    ingredient_id: string
    ordered_qty: string
    unit_cost: string
    notes?: string | null
  }>
}) =>
  apiFetch<{ id: string }>('/api/v1/purchase-orders', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const createGoodsReceiptRequest = (body: {
  location_id: string
  supplier_id?: string | null
  purchase_order_id?: string | null
  notes?: string | null
  confirm?: boolean
  items: Array<{
    ingredient_id: string
    received_qty: string
    unit_cost: string
    expiry_date?: string | null
  }>
}) =>
  apiFetch<GoodsReceiptOut>('/api/v1/goods-receipts', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const listSettingsRequest = () => apiFetch<SettingOut[]>('/api/v1/settings')
