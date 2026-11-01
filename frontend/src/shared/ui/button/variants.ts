import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@ui/cn'

export const buttonVariants = cva(
  cn(
    'inline-flex cursor-pointer items-center justify-center',
    'text-sm font-medium transition',
    'disabled:cursor-not-allowed disabled:opacity-50',
  ),
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        blank: 'underline-offset-2 hover:underline',
      },
      size: {
        default: 'min-h-10 gap-2 rounded-xl px-3.5',
        small: 'min-h-8 gap-1.5 rounded-lg px-3 text-xs',
        icon: 'size-10 rounded-xl',
        iconSmall: 'size-8 rounded-lg',
      },
    },
    defaultVariants: { variant: 'primary', size: 'default' },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
