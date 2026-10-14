import { describe, expect, it } from 'vitest'

import i18n, { applyDocumentDirection } from '@/lib/i18n'

describe('i18n direction', () => {
  it('sets rtl for arabic', async () => {
    await i18n.changeLanguage('ar')
    applyDocumentDirection('ar')
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
  })

  it('sets ltr for english', async () => {
    await i18n.changeLanguage('en')
    applyDocumentDirection('en')
    expect(document.documentElement.dir).toBe('ltr')
    expect(document.documentElement.lang).toBe('en')
  })
})
