import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import {
  listAuthors,
  listFavoriteGroups,
  listSeries,
  listTags,
} from '@/features/gallery/gallery-api'

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
    queryKey: computed(() => ['tags', tagSearch.value, sources.selectedTagIds()]),
    queryFn: () => listTags(tagSearch.value, sources.selectedTagIds()),
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const authorsQuery = useQuery({
    queryKey: computed(() => ['filter-authors', authorSearch.value, sources.authorId()]),
    queryFn: () => {
      const authorId = sources.authorId()
      return listAuthors(authorSearch.value, authorId === undefined ? [] : [authorId])
    },
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const seriesQuery = useQuery({
    queryKey: computed(() => ['filter-series', seriesSearch.value]),
    queryFn: () => listSeries(0, seriesSearch.value),
    enabled: computed(sources.open),
    placeholderData: (previousData) => previousData,
  })
  const favoriteGroupsQuery = useQuery({
    queryKey: ['favorite-groups'],
    queryFn: listFavoriteGroups,
    enabled: computed(sources.open),
  })

  return {
    tagSearch,
    authorSearch,
    seriesSearch,
    tags: computed(() => tagsQuery.data.value ?? []),
    authors: computed(() => authorsQuery.data.value ?? []),
    series: computed(() => seriesQuery.data.value?.items ?? []),
    favoriteGroups: computed(() => favoriteGroupsQuery.data.value ?? []),
    favoriteGroupsReady: favoriteGroupsQuery.isSuccess,
  }
}
