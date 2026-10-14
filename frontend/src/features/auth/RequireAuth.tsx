import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/features/auth/AuthContext'

export const RequireAuth = () => {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-stone-600">Loading…</div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
