<script setup lang="ts">
import { X } from '@lucide/vue'
import type { ClassValue } from 'clsx'
import {
  type FocusOutsideEvent,
  type PointerDownOutsideEvent,
  PopoverAnchor,
  PopoverContent,
  PopoverPortal,
  PopoverRoot,
} from 'reka-ui'
import { computed, nextTick, useId, useTemplateRef, watch } from 'vue'

import { Button } from '@ui/button'
import { cn } from '@ui/cn'
import { Input } from '@ui/input'

import { useAutocomplete } from './useAutocomplete'

const props = withDefaults(
  defineProps<{
    options: readonly string[]
    placeholder?: string
    disabled?: boolean
    onRemove?: ((value: string) => void) | undefined
    class?: ClassValue
  }>(),
  { placeholder: '', disabled: false, onRemove: undefined, class: '' },
)

const model = defineModel<string>({ default: '' })
const open = defineModel<boolean>('open', { default: false })
const anchor = useTemplateRef<HTMLDivElement>('anchor')
const viewport = useTemplateRef<HTMLDivElement>('viewport')
const listboxId = useId()
const {
  inputValue,
  filteredOptions,
  highlightedValue,
  visible,
  setOpen,
  updateInput,
  startComposition,
  finishComposition,
  select,
  handleKeydown,
} = useAutocomplete({ model, open, options: () => props.options, disabled: () => props.disabled })
const activeId = computed(() => {
  const index = filteredOptions.value.indexOf(highlightedValue.value ?? '')
  return visible.value && index >= 0 ? `${listboxId}-${String(index)}` : undefined
})

function handleCompositionEnd(event: CompositionEvent) {
  if (event.target instanceof HTMLInputElement) finishComposition(event.target.value)
}

function handleInteractOutside(event: FocusOutsideEvent | PointerDownOutsideEvent) {
  if (event.target instanceof Node && anchor.value?.contains(event.target)) event.preventDefault()
}

watch([highlightedValue, visible, filteredOptions], async () => {
  await nextTick()
  if (!visible.value) return
  const container = viewport.value
  const item = container?.querySelector<HTMLElement>('[data-highlighted]')
  if (!container || !item || container.clientHeight === 0) return

  // 只滚动候选容器，避免 scrollIntoView 连带移动页面。
  const bottom = item.offsetTop + item.offsetHeight
  if (item.offsetTop < container.scrollTop) container.scrollTop = item.offsetTop
  else if (bottom > container.scrollTop + container.clientHeight) {
    container.scrollTop = bottom - container.clientHeight
  }
})
</script>

<template>
  <PopoverRoot :open="visible" @update:open="setOpen">
    <PopoverAnchor as-child>
      <div ref="anchor" :class="cn('min-w-0', props.class)">
        <Input
          :model-value="inputValue"
          :placeholder="placeholder"
          :disabled="disabled"
          role="combobox"
          autocomplete="off"
          aria-autocomplete="list"
          :aria-expanded="visible"
          :aria-controls="visible ? listboxId : undefined"
          :aria-activedescendant="activeId"
          @update:model-value="updateInput"
          @focus="setOpen(true)"
          @click="setOpen(true)"
          @keydown="handleKeydown"
          @compositionstart="startComposition"
          @compositionend="handleCompositionEnd"
        />
      </div>
    </PopoverAnchor>
    <PopoverPortal v-if="visible">
      <PopoverContent
        as-child
        align="start"
        :side-offset="4"
        :collision-padding="8"
        @open-auto-focus.prevent
        @close-auto-focus.prevent
        @interact-outside="handleInteractOutside"
      >
        <div
          :id="listboxId"
          role="listbox"
          :class="
            cn(
              'z-50 flex max-h-(--reka-popover-content-available-height) w-(--reka-popover-trigger-width) flex-col overflow-hidden rounded-xl',
              'origin-(--reka-popover-content-transform-origin) border border-border bg-popover p-1 text-popover-foreground shadow-xl',
            )
          "
          data-app-floating-content
        >
          <div ref="viewport" class="relative max-h-72 min-h-0 overflow-y-auto overscroll-contain">
            <div
              v-for="(option, index) in filteredOptions"
              :id="`${listboxId}-${String(index)}`"
              :key="option"
              role="option"
              :aria-selected="model === option"
              :data-highlighted="highlightedValue === option ? '' : undefined"
              :class="
                cn(
                  'flex min-h-9 cursor-pointer items-center gap-2 rounded-lg py-1.5 pr-2 pl-3 text-sm outline-none',
                  'data-highlighted:bg-accent data-highlighted:text-accent-foreground',
                )
              "
              @pointerdown.prevent
              @pointermove="highlightedValue = option"
              @click="select(option)"
            >
              <span class="min-w-0 flex-1 wrap-break-word">{{ option }}</span>
              <Button
                v-if="props.onRemove"
                variant="ghost"
                size="iconSmall"
                class="size-6 shrink-0 rounded-md text-muted-foreground hover:text-destructive"
                :tabindex="-1"
                @pointerdown.stop.prevent
                @click.stop="props.onRemove?.(option)"
              >
                <X :size="14" />
              </Button>
            </div>
          </div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
