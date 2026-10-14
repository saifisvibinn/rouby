import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/AuthContext'
import { LanguageSwitcher } from '@/features/settings/LanguageSwitcher'

const loginSchema = z.object({
  email: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const LoginPage = () => {
  const { t } = useTranslation()
  const { login, user, isLoading } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  if (!isLoading && user) {
    return <Navigate to="/" replace />
  }

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    try {
      await login(values.email, values.password)
      navigate('/', { replace: true })
    } catch {
      setError(t('login.error'))
    }
  })

  return (
    <div className="flex min-h-dvh items-center justify-center p-4 safe-top pb-[max(1rem,env(safe-area-inset-bottom))]">
      <Card className="w-full max-w-md space-y-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-3xl font-semibold tracking-tight text-teal-800">{t('appName')}</p>
            <p className="mt-1 text-sm text-stone-500">{t('tagline')}</p>
          </div>
          <LanguageSwitcher />
        </div>
        <h1 className="text-xl font-medium text-stone-900">{t('login.title')}</h1>
        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          <div className="space-y-1">
            <label htmlFor="email" className="text-sm font-medium text-stone-700">
              {t('login.email')}
            </label>
            <Input id="email" type="text" autoComplete="username" {...register('email')} />
            {errors.email ? (
              <p className="text-xs text-red-600" role="alert">
                {errors.email.message}
              </p>
            ) : null}
          </div>
          <div className="space-y-1">
            <label htmlFor="password" className="text-sm font-medium text-stone-700">
              {t('login.password')}
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register('password')}
            />
            {errors.password ? (
              <p className="text-xs text-red-600" role="alert">
                {errors.password.message}
              </p>
            ) : null}
          </div>
          {error ? (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={isSubmitting} size="lg">
            {t('login.submit')}
          </Button>
        </form>
      </Card>
    </div>
  )
}
