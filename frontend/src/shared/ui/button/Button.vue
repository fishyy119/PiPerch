<script setup lang="ts">
import type { ClassValue } from 'clsx'

import { cn } from '@ui/cn'

import { type ButtonVariants, buttonVariants } from './variants'

const props = withDefaults(
  defineProps<{
    as?: 'button' | 'a'
    type?: 'button' | 'submit' | 'reset'
    variant?: NonNullable<ButtonVariants['variant']>
    size?: NonNullable<ButtonVariants['size']>
    disabled?: boolean
    class?: ClassValue
  }>(),
  { as: 'button', type: 'button', variant: 'primary', size: 'default', disabled: false, class: '' },
)
</script>

<template>
  <component
    :is="as"
    :type="as === 'button' ? type : undefined"
    :disabled="as === 'button' ? disabled : undefined"
    :class="
      cn(
        buttonVariants({
          variant: props.variant,
          size: props.variant === 'blank' ? null : props.size,
        }),
        props.class,
      )
    "
  >
    <slot />
  </component>
</template>
