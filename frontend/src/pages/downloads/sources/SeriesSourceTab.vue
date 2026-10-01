<script setup lang="ts">
import { Search } from '@lucide/vue'
import { ref } from 'vue'

import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Input from '@ui/Input.vue'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const sourceInput = ref('')
const { candidates, page, nextPage, emptyMessage, mutation, loadPage } = useDiscoveryPagination(
  (targetPage) => {
    const seriesId = Number(sourceInput.value.trim())
    if (!Number.isSafeInteger(seriesId) || seriesId <= 0) {
      throw new Error('请输入有效的正整数 ID。')
    }
    return { sourceType: 'series', seriesId, page: targetPage }
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
    <template #source>
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="loadPage(0)">
        <Input v-model="sourceInput" class="flex-1" placeholder="插画系列 ID" />
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
