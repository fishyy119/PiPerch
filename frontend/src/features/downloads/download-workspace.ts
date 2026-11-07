import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'

import type { DiscoveryRequest } from '@/features/discovery/discovery-api'

export const sourceOptions = [
  { value: 'artwork', label: '作品' },
  { value: 'search', label: '搜索' },
  { value: 'user', label: '用户' },
  { value: 'fanbox', label: 'FANBOX' },
  { value: 'followUpdates', label: '更新' },
  { value: 'bookmark', label: '收藏' },
  { value: 'series', label: '系列' },
] as const

type SourceType = (typeof sourceOptions)[number]['value']

export const useDownloadWorkspaceStore = defineStore('download-workspace', () => {
  const sourceType = ref<SourceType>('artwork')
  const sourceLabel = computed(
    () => sourceOptions.find((option) => option.value === sourceType.value)?.label ?? '作品',
  )
  const pendingPreviewRequest = ref<DiscoveryRequest | null>(null)

  function setSourceType(value: string) {
    const option = sourceOptions.find((item) => item.value === value)
    if (option !== undefined) sourceType.value = option.value
  }

  function requestPreview(request: DiscoveryRequest) {
    sourceType.value =
      request.sourceType === 'user' && request.source === 'fanbox' ? 'fanbox' : request.sourceType
    pendingPreviewRequest.value = request
  }

  function takePreviewRequest(type: SourceType) {
    const request = pendingPreviewRequest.value
    if (request === null) return null
    const target =
      request.sourceType === 'user' && request.source === 'fanbox' ? 'fanbox' : request.sourceType
    if (target !== type) return null
    pendingPreviewRequest.value = null
    return request
  }

  return {
    sourceType,
    sourceLabel,
    pendingPreviewRequest,
    setSourceType,
    requestPreview,
    takePreviewRequest,
  }
})

export function useDownloadWorkspaceState() {
  const store = useDownloadWorkspaceStore()
  const { setSourceType, requestPreview, takePreviewRequest } = store
  return {
    ...storeToRefs(store),
    setSourceType,
    requestPreview,
    takePreviewRequest,
  }
}
