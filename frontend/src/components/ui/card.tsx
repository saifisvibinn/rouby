import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export const Card = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn('rounded-xl border border-stone-200 bg-white/90 p-6 shadow-sm', className)}
    {...props}
  />
)
