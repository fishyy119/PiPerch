import type { QueryClient } from '@tanstack/vue-query'

import type { ArtworkDetail, ArtworkListFilters } from '@/features/artworks/artworks-api'

export const artworkQueryKeys = {
  all: ['artworks'] as const,
  list: (filters: ArtworkListFilters) => ['artworks', 'list', filters] as const,
  detail: (artworkId: number) => ['artworks', 'detail', artworkId] as const,
  related: (artworkId: number, limit: number) => ['artworks', 'related', artworkId, limit] as const,
  tags: (search: string, includeIds: number[]) => ['artworks', 'tags', search, includeIds] as const,
  authors: (search: string, includeIds: number[]) =>
    ['artworks', 'authors', search, includeIds] as const,
  series: (page: number, search: string) => ['artworks', 'series', page, search] as const,
}

export const groupQueryKeys = {
  all: ['groups'] as const,
  list: () => ['groups', 'list'] as const,
}

export function updateArtworkDetail(
  queryClient: QueryClient,
  artworkId: number,
  update: (artwork: ArtworkDetail) => ArtworkDetail,
) {
  queryClient.setQueryData<ArtworkDetail>(artworkQueryKeys.detail(artworkId), (artwork) =>
    artwork ? update(artwork) : artwork,
  )
}

export async function invalidateArtworkData(queryClient: QueryClient) {
  await queryClient.invalidateQueries({ queryKey: artworkQueryKeys.all })
}

export async function invalidateArtworkGroupData(queryClient: QueryClient) {
  await Promise.all([
    invalidateArtworkData(queryClient),
    queryClient.invalidateQueries({ queryKey: groupQueryKeys.all }),
  ])
}
