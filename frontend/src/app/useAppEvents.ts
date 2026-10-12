import { useQueryClient } from '@tanstack/vue-query'
import { onBeforeUnmount, onMounted } from 'vue'
import { z } from 'zod'

import { useLibraryMembershipStore } from '@/features/library/library-membership'

const libraryChangeSchema = z.object({
  artworkIds: z.array(z.number().int().positive()),
})

export function useAppEvents() {
  const library = useLibraryMembershipStore()
  const queryClient = useQueryClient()
  let events: EventSource | undefined

  function refreshJobs() {
    void queryClient.invalidateQueries({ queryKey: ['download-jobs'] })
  }

  function handleLibraryChange(event: Event, inLibrary: boolean) {
    try {
      if (!(event instanceof MessageEvent) || typeof event.data !== 'string') return
      const { artworkIds } = libraryChangeSchema.parse(JSON.parse(event.data) as unknown)
      library.applyChange(artworkIds, inLibrary)
    } catch {
      // 忽略无效事件，保留当前图库状态。
    }
  }

  onMounted(() => {
    events = new EventSource('/api/events/downloads')
    events.addEventListener('job-updated', refreshJobs)
    events.addEventListener('library-added', (event) => handleLibraryChange(event, true))
    events.addEventListener('library-removed', (event) => handleLibraryChange(event, false))
  })

  onBeforeUnmount(() => {
    events?.close()
  })
}
