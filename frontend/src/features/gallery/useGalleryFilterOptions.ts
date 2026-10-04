import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { listAuthors, listSeries, listTags } from '@/features/artworks/artworks-api'
import { listGroups } from '@/features/groups/groups-api'
import { artworkQueryKeys, groupQueryKeys } from '@/features/library/library-query-cache'

interface GalleryFilterOptionSources {
  open: () => boolean
  selectedTagIds: () => number[]
  authorId: () => number | undefined
}

export function useGalleryFilterOptions(sources: GalleryFilterOptionSources) {
  const tagSearch = ref('')
  const authorSearch = ref('')
  const seriesSearch = ref('')

  const tagsQuery = useQuery({
    queryKey: computed(() => artworkQueryKeys.tags(tagSearch.value, sources.selectedTagIds())),
    queryFn: () => listTags(tagSearch.value, sources.selectedTagIds()),
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const authorsQuery = useQuery({
    queryKey: computed(() => {
      const authorId = sources.authorId()
      return artworkQueryKeys.authors(authorSearch.value, authorId === undefined ? [] : [authorId])
    }),
    queryFn: () => {
      const authorId = sources.authorId()
      return listAuthors(authorSearch.value, authorId === undefined ? [] : [authorId])
    },
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const seriesQuery = useQuery({
    queryKey: computed(() => artworkQueryKeys.series(0, seriesSearch.value)),
    queryFn: () => listSeries(0, seriesSearch.value),
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const groupsQuery = useQuery({
    queryKey: groupQueryKeys.list(),
    queryFn: listGroups,
    enabled: computed(sources.open),
  })

  return {
    tagSearch,
    authorSearch,
    seriesSearch,
    tags: computed(() => tagsQuery.data.value ?? []),
    authors: computed(() => authorsQuery.data.value ?? []),
    series: computed(() => seriesQuery.data.value?.items ?? []),
    groups: computed(() => groupsQuery.data.value ?? []),
    groupsReady: groupsQuery.isSuccess,
  }
}
