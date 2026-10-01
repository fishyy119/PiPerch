<script setup lang="ts">
import { Search } from '@lucide/vue'
import { ref } from 'vue'

import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Textarea from '@ui/Textarea.vue'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const sourceInput = ref('')
const { candidates, page, nextPage, emptyMessage, mutation, loadPage } = useDiscoveryPagination(
  (targetPage) => {
    const inputs = sourceInput.value
      .trim()
      .split(/[\s,]+/u)
      .map((item) => item.trim())
      .filter(Boolean)
    if (inputs.length === 0) throw new Error('请输入至少一个作品 URL 或 ID。')
    return { sourceType: 'artwork', inputs, page: targetPage }
  },
)
</script>

<template>
  <DiscoverySourceLayout
    :candidates="candidates"
    :page="page"
    :next-page="nextPage"
    :pending="mutation.isPending.value"
    :empty-message="emptyMessage"
    @load-page="loadPage"
  >
    <template #tabs><slot name="tabs" /></template>
    <template #source>
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="loadPage(0)">
        <Textarea
          v-model="sourceInput"
          class="flex-1 resize-y"
          placeholder="作品 URL 或 ID，每行一个"
        />
        <Button type="submit" class="sm:self-start" :disabled="mutation.isPending.value">
          <Search :size="18" />
          {{ mutation.isPending.value ? '加载中…' : '预览' }}
        </Button>
      </form>
      <p v-if="mutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(mutation.error.value) }}
      </p>
    </template>
  </DiscoverySourceLayout>
</template>
