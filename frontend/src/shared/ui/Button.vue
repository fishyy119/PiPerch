<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    as?: 'button' | 'a'
    type?: 'button' | 'submit' | 'reset'
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
    size?: 'default' | 'small' | 'icon' | 'iconSmall'
    disabled?: boolean
  }>(),
  { as: 'button', type: 'button', variant: 'primary', size: 'default', disabled: false },
)

const variantClasses = {
  primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
  secondary: 'border-input bg-background hover:bg-accent hover:text-accent-foreground border',
  danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
  ghost: 'hover:bg-accent hover:text-accent-foreground',
} as const

const sizeClasses = {
  default: 'min-h-10 gap-2 rounded-xl px-3.5',
  small: 'min-h-8 gap-1.5 rounded-lg px-3 text-xs',
  icon: 'size-10 rounded-xl',
  iconSmall: 'size-8 rounded-lg',
} as const
</script>

<template>
  <component
    :is="as"
    :type="as === 'button' ? type : undefined"
    :disabled="as === 'button' ? disabled : undefined"
    class="inline-flex cursor-pointer items-center justify-center text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
    :class="[variantClasses[props.variant], sizeClasses[props.size]]"
  >
    <slot />
  </component>
</template>
