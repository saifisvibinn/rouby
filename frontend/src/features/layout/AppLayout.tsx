import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthContext'
import { LanguageSwitcher } from '@/features/settings/LanguageSwitcher'
import { cn } from '@/lib/utils'

const navItems: Array<{ to: string; key: string; end?: boolean }> = [
  { to: '/', key: 'dashboard', end: true },
  { to: '/pos', key: 'pos' },
  { to: '/products', key: 'products' },
  { to: '/ingredients', key: 'ingredients' },
  { to: '/inventory', key: 'inventory' },
  { to: '/purchasing', key: 'purchasing' },
  { to: '/reports', key: 'reports' },
  { to: '/settings', key: 'settings' },
]

export const AppLayout = () => {
  const { t } = useTranslation()
  const { logout, user } = useAuth()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!menuOpen) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'flex min-h-11 items-center rounded-lg px-3 py-2.5 text-base text-stone-700 hover:bg-stone-100 lg:min-h-0 lg:text-sm',
      isActive && 'bg-teal-50 font-medium text-teal-900',
    )

  const sidebar = (
    <>
      <div className="mb-6 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-xl font-semibold text-teal-800">{t('appName')}</p>
          <p className="truncate text-xs text-stone-500">{user?.full_name}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <LanguageSwitcher />
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" aria-hidden />
          </Button>
        </div>
      </div>
      <nav className="flex flex-col gap-1" aria-label="Main">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
            {t(`nav.${item.key}`)}
          </NavLink>
        ))}
      </nav>
      <Button
        variant="ghost"
        className="mt-6 min-h-11 w-full justify-start lg:min-h-10"
        onClick={logout}
      >
        {t('nav.logout')}
      </Button>
    </>
  )

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[240px_1fr]">
      <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-stone-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden safe-top">
        <div className="min-w-0">
          <p className="truncate text-lg font-semibold text-teal-800">{t('appName')}</p>
          <p className="truncate text-xs text-stone-500">{user?.full_name}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="min-h-11 min-w-11 shrink-0 px-0"
          onClick={() => setMenuOpen(true)}
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" aria-hidden />
        </Button>
      </header>

      {menuOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-stone-950/40 lg:hidden"
          aria-label="Close menu overlay"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}

      <aside
        id="mobile-nav"
        className={cn(
          'fixed inset-y-0 start-0 z-50 w-[min(100%,20rem)] border-e border-stone-200 bg-white p-4 shadow-xl transition-transform duration-200 ease-out lg:static lg:z-auto lg:block lg:w-auto lg:translate-x-0 lg:border-e lg:bg-white/80 lg:p-4 lg:shadow-none',
          menuOpen ? 'translate-x-0' : '-translate-x-full rtl:translate-x-full lg:translate-x-0',
        )}
      >
        {sidebar}
      </aside>

      <main className="px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-6 sm:py-6">
        <Outlet />
      </main>
    </div>
  )
}
