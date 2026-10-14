import { expect, test } from '@playwright/test'

const saleId = '11111111-1111-4111-8111-111111111111'
const branchId = '22222222-2222-4222-8222-222222222222'
const userId = '33333333-3333-4333-8333-333333333333'
const productId = '44444444-4444-4444-8444-444444444444'
const variantId = '55555555-5555-4555-8555-555555555555'
const doubleWheyId = '66666666-6666-4666-8666-666666666666'
const noBananaId = '77777777-7777-4777-8777-777777777777'

const saleResponse = {
  id: saleId,
  status: 'CONFIRMED',
  order_type: 'dine_in',
  branch_id: branchId,
  user_id: userId,
  subtotal: '160.00',
  discount: '0.00',
  tax: '0.00',
  total: '160.00',
  cogs_total: '102.00',
  flagged_negative_stock: false,
  items: [
    {
      id: '88888888-8888-4888-8888-888888888888',
      variant_id: variantId,
      recipe_version_id: null,
      qty: 1,
      unit_price: '160.00',
      line_total: '160.00',
      notes: null,
      cogs: '102.00',
      modifiers: [
        { id: '99999999-9999-4999-8999-999999999999', modifier_id: doubleWheyId, price_delta: '40.00' },
        { id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', modifier_id: noBananaId, price_delta: '0.00' },
      ],
      consumptions: [],
    },
  ],
  payments: [],
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-15T00:00:00Z',
}

test('operator can create a split-payment POS sale', async ({ page }) => {
  await page.route('http://localhost:8000/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/v1/auth/login' && request.method() === 'POST') {
      await route.fulfill({
        json: {
          access_token: 'access-token',
          refresh_token: 'refresh-token',
          token_type: 'bearer',
        },
      })
      return
    }

    if (path === '/api/v1/auth/me' && request.method() === 'GET') {
      await route.fulfill({
        json: {
          id: userId,
          email: 'admin@rouby.app',
          full_name: 'Admin',
          roles: [{ code: 'operator', name_en: 'Operator', name_ar: 'مشغل' }],
          permissions: ['sales.view', 'sales.create'],
          branch_id: branchId,
        },
      })
      return
    }

    if (path === '/api/v1/pos/menu' && request.method() === 'GET') {
      await route.fulfill({
        json: [
          {
            id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
            code: 'PROTEIN_SHAKES',
            name_en: 'Protein Shakes',
            name_ar: 'مشروبات بروتين',
            products: [
              {
                id: productId,
                sku: 'BANANA_PROTEIN_SHAKE',
                name_en: 'Banana Protein Shake',
                name_ar: 'مخفوق بروتين بالموز',
                image_url: null,
                modifier_groups: [
                  {
                    id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
                    code: 'NUTRITION',
                    name_en: 'Nutrition Options',
                    name_ar: 'خيارات التغذية',
                    min_select: 0,
                    max_select: 4,
                    modifiers: [
                      {
                        id: doubleWheyId,
                        code: 'DOUBLE_WHEY',
                        name_en: 'Double Whey',
                        name_ar: 'واي مضاعف',
                        price_delta: '40.00',
                      },
                      {
                        id: noBananaId,
                        code: 'NO_BANANA',
                        name_en: 'No Banana',
                        name_ar: 'بدون موز',
                        price_delta: '0.00',
                      },
                    ],
                  },
                ],
                variants: [
                  {
                    id: variantId,
                    sku: 'BANANA_PROTEIN_SHAKE',
                    name_en: 'Regular',
                    name_ar: 'عادي',
                    price: '120.00',
                    available: true,
                  },
                ],
              },
            ],
          },
        ],
      })
      return
    }

    if (path === '/api/v1/sales' && request.method() === 'POST') {
      await route.fulfill({ json: { ...saleResponse, status: 'DRAFT', payments: [] } })
      return
    }

    if (path === `/api/v1/sales/${saleId}/payments` && request.method() === 'POST') {
      const body = request.postDataJSON() as { method: string; amount: string }
      await route.fulfill({
        json: {
          id: crypto.randomUUID(),
          sale_id: saleId,
          method: body.method,
          amount: body.amount,
          created_at: '2026-10-15T00:00:01Z',
        },
      })
      return
    }

    if (path === `/api/v1/sales/${saleId}/confirm` && request.method() === 'POST') {
      await route.fulfill({ json: saleResponse })
      return
    }

    await route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: path } } })
  })

  await page.goto('/login')
  await page.getByLabel('Username').fill('admin')
  await page.getByLabel('Password').fill('admin')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await page.getByRole('link', { name: 'POS' }).click()
  await expect(page.getByRole('heading', { name: 'Point of Sale' })).toBeVisible()

  await page.getByRole('button', { name: /Banana Protein Shake/ }).click()
  await page.getByRole('button', { name: /Double Whey/ }).click()
  await page.getByRole('button', { name: /No Banana/ }).click()
  await page.getByRole('button', { name: 'Add to cart' }).click()

  await page.getByRole('button', { name: 'Split' }).click()
  await page.getByLabel('Cash').fill('80')
  await page.getByLabel('Card').fill('80')
  await page.getByRole('button', { name: 'Confirm sale' }).click()

  await expect(page.getByText('Sale confirmed and receipt ready.')).toBeVisible()
  await expect(page.getByText('Payment complete. Thank you.')).toBeVisible()
  await expect(page.getByText('1 x Banana Protein Shake')).toBeVisible()
})
