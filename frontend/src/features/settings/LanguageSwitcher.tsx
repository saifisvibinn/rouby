import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { applyDocumentDirection } from '@/lib/i18n'

export const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation()

  const handleToggle = () => {
    const next = i18n.language.startsWith('ar') ? 'en' : 'ar'
    void i18n.changeLanguage(next).then(() => applyDocumentDirection(next))
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={handleToggle}
      aria-label={t('language')}
    >
      {i18n.language.startsWith('ar') ? 'EN' : 'عربي'}
    </Button>
  )
}
