<script setup lang="ts">
import type { MultiValueMatch } from '@/features/artworks/artworks-api'

const model = defineModel<MultiValueMatch>({ required: true })

const options = [
  { value: 'any', label: '或' },
  { value: 'all', label: '与' },
] as const
</script>

<template>
  <button
    type="button"
    class="inline-flex cursor-pointer rounded-md bg-muted p-0.5 font-normal"
    @click="model = model === 'any' ? 'all' : 'any'"
  >
    <span
      v-for="option in options"
      :key="option.value"
      class="min-w-5 rounded-sm px-1 py-0.5 text-[0.6875rem] leading-none transition"
      :class="
        model === option.value
          ? 'bg-primary text-primary-foreground shadow-sm'
          : 'text-muted-foreground hover:text-foreground'
      "
    >
      {{ option.label }}
    </span>
  </button>
</template>
