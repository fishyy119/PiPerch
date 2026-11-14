import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@ui/cn'

export const dialogContentVariants = cva('fixed z-50 border-border shadow-2xl', {
  variants: {
    position: {
      center: cn(
        'top-1/2 left-1/2 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2',
        'rounded-xl border bg-card p-6 text-card-foreground',
      ),
      top: cn(
        'top-16 right-0 left-0 max-h-[calc(100vh-4rem)] overflow-y-auto',
        'border-b bg-popover text-popover-foreground',
      ),
    },
  },
  defaultVariants: { position: 'center' },
})

export const dialogOverlayVariants = cva('fixed inset-0 z-40', {
  variants: {
    position: {
      center: 'bg-foreground/55 dark:bg-background/55',
      top: 'bg-foreground/20 dark:bg-background/20',
    },
  },
  defaultVariants: { position: 'center' },
})

export type DialogContentVariants = VariantProps<typeof dialogContentVariants>
