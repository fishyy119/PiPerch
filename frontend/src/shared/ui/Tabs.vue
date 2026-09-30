<script setup lang="ts">
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'

export interface TabOption {
  value: string
  label: string
  disabled?: boolean
}

defineProps<{ items: readonly TabOption[] }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <TabsRoot v-model="model">
    <TabsList class="inline-flex rounded-xl bg-muted p-1">
      <TabsTrigger
        v-for="item in items"
        :key="item.value"
        :value="item.value"
        :disabled="item.disabled === true"
        :class="[
          'min-h-8 cursor-pointer rounded-lg px-3',
          'text-sm font-medium text-muted-foreground transition',
          'data-[state=active]:bg-background data-[state=active]:text-foreground',
          'data-disabled:cursor-not-allowed data-disabled:opacity-50',
        ]"
      >
        {{ item.label }}
      </TabsTrigger>
    </TabsList>
    <TabsContent v-for="item in items" :key="item.value" :value="item.value" class="mt-4">
      <slot :name="item.value" :item="item">
        <slot :item="item" />
      </slot>
    </TabsContent>
  </TabsRoot>
</template>
