<script setup lang="ts">
import type { Component } from 'vue'

import Card from '@ui/Card.vue'

defineProps<{
  sectionId: string
  title: string
  description: string
  icon: Component
}>()
</script>

<template>
  <Card :id="sectionId" as="section" class="scroll-mt-20">
    <header class="flex items-start gap-3 border-b border-border px-5 py-5 md:px-6">
      <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/15 text-primary">
        <component :is="icon" :size="21" />
      </span>
      <div class="min-w-0">
        <h2 class="font-semibold">{{ title }}</h2>
        <p class="mt-1 text-sm text-muted-foreground">{{ description }}</p>
      </div>
    </header>
    <div class="divide-y divide-border px-5 md:px-6">
      <slot />
    </div>
  </Card>
</template>
