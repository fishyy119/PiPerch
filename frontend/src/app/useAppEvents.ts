import { useQueryClient } from '@tanstack/vue-query'
import { onBeforeUnmount, onMounted } from 'vue'
import { z } from 'zod'

import { libraryArtworkReferenceSchema } from '@/features/artworks/artwork-source'
import { useLibraryMembershipStore } from '@/features/library/library-membership'

const libraryChangeSchema = z.object({
  references: z.array(libraryArtworkReferenceSchema),
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
      const { references } = libraryChangeSchema.parse(JSON.parse(event.data) as unknown)
      for (const item of references) {
        library.applyReference(item, inLibrary)
      }
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
