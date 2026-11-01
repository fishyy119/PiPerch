<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from 'reka-ui'

import { cn } from '@ui/cn'

import {
  type DialogContentVariants,
  dialogContentVariants,
  dialogOverlayVariants,
} from './variants'

withDefaults(
  defineProps<{
    title?: string
    description?: string
    position?: NonNullable<DialogContentVariants['position']>
    modal?: boolean
    contentClass?: string
    overlayClass?: string
    titleClass?: string
  }>(),
  {
    title: '',
    description: '',
    position: 'center',
    modal: true,
    contentClass: '',
    overlayClass: '',
    titleClass: '',
  },
)

const open = defineModel<boolean>('open', { default: false })

function close() {
  open.value = false
}
</script>

<template>
  <DialogRoot v-model:open="open" :modal="modal">
    <DialogTrigger v-if="$slots.trigger" as-child>
      <slot name="trigger" />
    </DialogTrigger>
    <DialogPortal>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogOverlay
          v-if="open"
          force-mount
          :class="cn(dialogOverlayVariants({ position }), overlayClass)"
        />
      </Transition>
      <Transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <DialogContent
          v-if="open"
          force-mount
          :class="cn(dialogContentVariants({ position }), contentClass)"
        >
          <DialogTitle v-if="title || $slots.title" :class="cn('font-semibold', titleClass)">
            <slot name="title">{{ title }}</slot>
          </DialogTitle>
          <DialogDescription
            v-if="description || $slots.description"
            class="mt-2 text-sm leading-6 text-muted-foreground"
          >
            <slot name="description">{{ description }}</slot>
          </DialogDescription>
          <slot :close="close" />
        </DialogContent>
      </Transition>
    </DialogPortal>
  </DialogRoot>
</template>
