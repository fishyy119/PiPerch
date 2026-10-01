<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description?: string
    controlId?: string
    disabled?: boolean
    layout?: 'compact' | 'expanded'
  }>(),
  { description: '', controlId: '', disabled: false, layout: 'compact' },
)
</script>

<template>
  <div
    data-setting-item
    :data-disabled="disabled || undefined"
    :data-layout="layout"
    :class="[
      'py-5',
      layout === 'compact'
        ? 'grid grid-cols-[minmax(12rem,0.8fr)_minmax(0,1.2fr)] items-center gap-8'
        : 'space-y-4',
      disabled ? 'opacity-50' : '',
    ]"
  >
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <label v-if="controlId" :for="controlId" class="text-sm font-medium">{{ title }}</label>
        <span v-else class="text-sm font-medium">{{ title }}</span>
        <slot name="status" />
      </div>
      <p v-if="description" class="mt-1 text-xs leading-5 text-muted-foreground">
        {{ description }}
      </p>
    </div>
    <div class="min-w-0">
      <slot />
    </div>
  </div>
</template>
