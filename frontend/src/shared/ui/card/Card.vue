<script setup lang="ts">
withDefaults(
  defineProps<{
    as?: 'div' | 'section' | 'article' | 'aside' | 'form' | 'button'
  }>(),
  { as: 'div' },
)
</script>

<template>
  <component
    :is="as"
    class="rounded-xl border border-border bg-card text-card-foreground shadow-sm shadow-foreground/8 dark:shadow-background/40"
  >
    <slot />
  </component>
</template>
