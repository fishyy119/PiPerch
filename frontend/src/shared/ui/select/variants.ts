import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@ui/cn'

export const selectTriggerVariants = cva(
  cn(
    'flex cursor-pointer items-center justify-between',
    'border border-input bg-background text-sm text-foreground',
    'disabled:cursor-not-allowed disabled:opacity-50',
  ),
  {
    variants: {
      size: {
        default: 'min-h-10 min-w-40 gap-3 rounded-xl px-3 py-2',
        small: 'min-h-9 min-w-24 gap-2 rounded-lg px-3 py-1',
      },
    },
    defaultVariants: { size: 'default' },
  },
)

export type SelectTriggerVariants = VariantProps<typeof selectTriggerVariants>
