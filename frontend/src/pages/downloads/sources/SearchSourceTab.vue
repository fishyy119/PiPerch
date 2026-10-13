<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed, ref } from 'vue'

import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Input from '@ui/Input.vue'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const keywordInput = ref('')
const submittedKeyword = ref('')
const { candidates, page, nextPage, mutation, loadPage, reset } = useDiscoveryPagination(
  (targetPage) => ({
    sourceType: 'search',
    keyword: submittedKeyword.value,
    page: targetPage,
  }),
)
const emptyMessage = computed(() => {
  if (!submittedKeyword.value) return '请输入搜索内容。'
  if (mutation.isPending.value) return '正在搜索作品…'
  if (mutation.error.value) return '搜索失败，请重试。'
  return '这一页没有找到匹配的作品。'
})

function search() {
  const keyword = keywordInput.value.trim()
  if (!keyword || mutation.isPending.value) return
  submittedKeyword.value = keyword
  reset()
  loadPage(0)
}
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
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="search">
        <Input v-model="keywordInput" class="flex-1" placeholder="输入搜索内容" />
        <Button
          type="submit"
          class="sm:self-start"
          :disabled="!keywordInput.trim() || mutation.isPending.value"
        >
          <Search :size="18" />
          {{ mutation.isPending.value ? '搜索中…' : '搜索' }}
        </Button>
      </form>
      <p v-if="mutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(mutation.error.value) }}
      </p>
    </template>
  </DiscoverySourceLayout>
</template>
