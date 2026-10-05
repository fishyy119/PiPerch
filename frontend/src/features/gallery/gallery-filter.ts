import { inject, type InjectionKey, provide, type Ref } from 'vue'

import type { MultiValueMatch } from '@/features/artworks/artworks-api'

export interface GalleryFilterValues {
  selectedTagIds: number[]
  tagMatch: MultiValueMatch
  authorId: number | undefined
  seriesId: number | undefined
  artworkType: string
  rating: string
  ai: string
  favorite: string
  selectedGroupIds: number[]
  groupMatch: MultiValueMatch
  sort: string
  order: string
  randomSeed: number
}

export type GalleryFilterUpdate = Partial<GalleryFilterValues>

interface GalleryFilterContext {
  filters: Ref<GalleryFilterValues>
  update: (update: GalleryFilterUpdate) => void
}

const galleryFilterContextKey: InjectionKey<GalleryFilterContext> = Symbol('gallery-filters')

export const GALLERY_RANDOM_SEED_MODULUS = 2_147_483_647

export function provideGalleryFilters(filters: Ref<GalleryFilterValues>) {
  provide(galleryFilterContextKey, {
    filters,
    update(update) {
      filters.value = { ...filters.value, ...update }
    },
  })
}

export function useGalleryFilters() {
  const context = inject(galleryFilterContextKey)
  if (context === undefined) throw new Error('Gallery filter context is not available')
  return context
}

export function defaultGalleryFilterValues(): GalleryFilterValues {
  return {
    selectedTagIds: [],
    tagMatch: 'any',
    authorId: undefined,
    seriesId: undefined,
    artworkType: '',
    rating: 'all',
    ai: 'all',
    favorite: 'all',
    selectedGroupIds: [],
    groupMatch: 'any',
    sort: 'downloadedAt',
    order: 'desc',
    randomSeed: 0,
  }
}
