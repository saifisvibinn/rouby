import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Card } from '@/components/ui/card'
import { useAuth } from '@/features/auth/AuthContext'
import { LanguageSwitcher } from '@/features/settings/LanguageSwitcher'
import { listSettingsRequest } from '@/lib/api'

export const SettingsPage = () => {
  const { t } = useTranslation()
  const { user } = useAuth()
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: listSettingsRequest })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">{t('nav.settings')}</h1>
        <p className="mt-2 max-w-2xl text-stone-600">
          Language, operator profile, and store policy settings.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Operator</h2>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-stone-500">Name</dt>
              <dd className="font-medium text-stone-900">{user?.full_name}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Login</dt>
              <dd className="font-medium text-stone-900">{user?.email}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Roles</dt>
              <dd className="font-medium text-stone-900">
                {user?.roles.map((role) => role.code).join(', ') || '—'}
              </dd>
            </div>
          </dl>
          <div className="border-t border-stone-200 pt-4">
            <p className="mb-2 text-sm font-medium text-stone-700">{t('language')}</p>
            <LanguageSwitcher />
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Store settings</h2>
          {settingsQuery.isLoading ? (
            <p className="text-sm text-stone-500">Loading…</p>
          ) : (
            <dl className="space-y-4">
              {(settingsQuery.data ?? []).map((setting) => (
                <div key={setting.id} className="rounded-lg border border-stone-200 px-3 py-2">
                  <dt className="text-xs font-medium uppercase tracking-wide text-stone-500">
                    {setting.key}
                  </dt>
                  <dd className="mt-1 text-base font-semibold text-stone-900">{setting.value}</dd>
                  {setting.description ? (
                    <p className="mt-1 text-xs text-stone-500">{setting.description}</p>
                  ) : null}
                </div>
              ))}
            </dl>
          )}
        </Card>
      </div>
    </div>
  )
}
