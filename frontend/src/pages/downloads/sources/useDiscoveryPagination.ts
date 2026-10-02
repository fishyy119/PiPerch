import { useMutation } from '@tanstack/vue-query'
import { ref } from 'vue'

import {
  discover,
  type DiscoveryItem,
  type DiscoveryRequest,
} from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'

export function useDiscoveryPagination(makeRequest: (page: number) => DiscoveryRequest) {
  const selection = useDownloadSelection()
  const candidates = ref<DiscoveryItem[]>([])
  const page = ref(0)
  const nextPage = ref<number | null>(null)
  const emptyMessage = ref('请先输入来源并预览。')

  const mutation = useMutation({
    mutationFn: async (targetPage: number) => discover(makeRequest(targetPage)),
    onSuccess: (result) => {
      candidates.value = result.items
      selection.remember(result.items)
      selection.removeAll(result.items.filter((item) => item.inLibrary))
      page.value = result.page
      nextPage.value = result.nextPage
      emptyMessage.value = result.items.length === 0 ? '这一页没有找到候选作品。' : ''
    },
  })

  function loadPage(targetPage: number) {
    mutation.mutate(targetPage)
  }

  return { candidates, page, nextPage, emptyMessage, mutation, loadPage }
}
