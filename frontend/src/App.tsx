import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/features/auth/AuthContext'
import { LoginPage } from '@/features/auth/LoginPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { IngredientsPage } from '@/features/ingredients/IngredientsPage'
import { InventoryPage } from '@/features/inventory/InventoryPage'
import { AppLayout } from '@/features/layout/AppLayout'
import { PosPage } from '@/features/pos/PosPage'
import { ProductsPage } from '@/features/products/ProductsPage'
import { PurchasingPage } from '@/features/purchasing/PurchasingPage'
import { ReportsPage } from '@/features/reports/ReportsPage'
import { ScannerPage } from '@/features/scanner/ScannerPage'
import { SettingsPage } from '@/features/settings/SettingsPage'

const queryClient = new QueryClient()

export const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/scanner" element={<ScannerPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="pos" element={<PosPage />} />
              <Route path="products" element={<ProductsPage />} />
              <Route path="ingredients" element={<IngredientsPage />} />
              <Route path="inventory" element={<InventoryPage />} />
              <Route path="purchasing" element={<PurchasingPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </QueryClientProvider>
)

export default App
