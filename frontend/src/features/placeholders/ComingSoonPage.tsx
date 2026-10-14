import { useTranslation } from 'react-i18next'

import { Card } from '@/components/ui/card'

export const ComingSoonPage = ({ titleKey }: { titleKey: string }) => {
  const { t } = useTranslation()
  return (
    <Card>
      <h1 className="text-xl font-semibold text-stone-900">{t(`nav.${titleKey}`)}</h1>
      <p className="mt-2 text-stone-600">{t('comingSoon')}</p>
    </Card>
  )
}
