import { describe, expect, it } from 'vitest'
import { z } from 'zod'

const loginSchema = z.object({
  email: z.string().min(1),
  password: z.string().min(1),
})

describe('loginSchema', () => {
  it('accepts username credentials shape', () => {
    const result = loginSchema.safeParse({
      email: 'admin',
      password: 'admin',
    })
    expect(result.success).toBe(true)
  })

  it('rejects empty password', () => {
    const result = loginSchema.safeParse({
      email: 'admin',
      password: '',
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty username', () => {
    const result = loginSchema.safeParse({
      email: '',
      password: 'admin',
    })
    expect(result.success).toBe(false)
  })
})
