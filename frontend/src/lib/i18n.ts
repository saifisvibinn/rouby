import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import ar from '@/locales/ar.json'
import en from '@/locales/en.json'

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

export const applyDocumentDirection = (lng: string) => {
  const dir = lng.startsWith('ar') ? 'rtl' : 'ltr'
  document.documentElement.lang = lng
  document.documentElement.dir = dir
}

i18n.on('languageChanged', applyDocumentDirection)
applyDocumentDirection(i18n.language)

export default i18n
