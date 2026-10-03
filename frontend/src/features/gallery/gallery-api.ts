import { z } from 'zod'

import { artworkTypeSchema } from '@/features/artworks/artwork'
import { api } from '@/shared/api/http'

export const tagSchema = z.object({
  tagId: z.number().int(),
  name: z.string(),
  translatedName: z.string().nullable(),
  artworkCount: z.number().int().nullable().optional(),
})
export type Tag = z.infer<typeof tagSchema>

export const artworkSummarySchema = z.object({
  artworkId: z.number().int().positive(),
  title: z.string(),
  artworkType: artworkTypeSchema,
  authorId: z.number().int().positive(),
  authorName: z.string(),
  seriesId: z.number().int().positive().nullable(),
  seriesTitle: z.string().nullable(),
  pageCount: z.number().int().positive(),
  xRestrict: z.number().int().nonnegative(),
  isAi: z.boolean(),
  publishedAt: z.string().nullable(),
  downloadedAt: z.string(),
  isFavorite: z.boolean(),
  favoriteGroupIds: z.array(z.number().int().positive()),
})
export type ArtworkSummary = z.infer<typeof artworkSummarySchema>

const artworkPageSchema = z.object({
  items: z.array(artworkSummarySchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})

const namedCountPageSchema = z.object({
  items: z.array(
    z.object({
      itemId: z.number().int().positive(),
      name: z.string(),
      count: z.number().int(),
      subtitle: z.string().nullable(),
    }),
  ),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})
export type NamedCount = z.infer<typeof namedCountPageSchema>['items'][number]

export const artworkDetailSchema = artworkSummarySchema.extend({
  description: z.string(),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  tags: z.array(tagSchema),
  media: z.array(
    z.object({
      role: z.string(),
      pageIndex: z.number().int().nullable(),
      mimeType: z.string(),
      byteSize: z.number().int(),
    }),
  ),
  ugoiraFrames: z.array(z.object({ fileName: z.string(), delayMs: z.number().int() })),
})
export type ArtworkDetail = z.infer<typeof artworkDetailSchema>

export interface GalleryFilters {
  page: number
  size: number
  search: string
  tagIds: number[]
  authorId?: number
  seriesId?: number
  artworkType?: string
  rating: string
  ai: string
  favorite: string
  favoriteGroupIds: number[]
  sort: string
  order: string
}

function galleryQuery(filters: GalleryFilters) {
  const params = new URLSearchParams({
    page: String(filters.page),
    size: String(filters.size),
    search: filters.search,
    rating: filters.rating,
    ai: filters.ai,
    favorite: filters.favorite,
    sort: filters.sort,
    order: filters.order,
  })
  filters.tagIds.forEach((id) => params.append('tagId', String(id)))
  filters.favoriteGroupIds.forEach((id) => params.append('favoriteGroupId', String(id)))
  if (filters.authorId !== undefined) params.set('authorId', String(filters.authorId))
  if (filters.seriesId !== undefined) params.set('seriesId', String(filters.seriesId))
  if (filters.artworkType) params.set('artworkType', filters.artworkType)
  return params
}

export async function listArtworks(filters: GalleryFilters) {
  return artworkPageSchema.parse(
    await api.get<unknown>(`/api/artworks?${galleryQuery(filters).toString()}`),
  )
}

export async function listTags(search = '') {
  return z
    .array(tagSchema)
    .parse(await api.get<unknown>(`/api/tags?search=${encodeURIComponent(search)}&limit=100`))
}

export async function listNamed(kind: 'authors' | 'series', page: number, search: string) {
  const params = new URLSearchParams({ page: String(page), search })
  return namedCountPageSchema.parse(await api.get<unknown>(`/api/${kind}?${params.toString()}`))
}

export async function getArtwork(artworkId: number) {
  return artworkDetailSchema.parse(await api.get<unknown>(`/api/artworks/${String(artworkId)}`))
}

export async function listRelatedArtworks(artworkId: number, limit = 12) {
  return z
    .array(artworkSummarySchema)
    .parse(
      await api.get<unknown>(`/api/artworks/${String(artworkId)}/related?limit=${String(limit)}`),
    )
}

export async function deleteArtwork(artworkId: number) {
  return z
    .object({ deleted: z.number().int() })
    .parse(await api.delete<unknown>(`/api/artworks/${String(artworkId)}`))
}

export async function bulkDeleteArtworks(artworkIds: number[]) {
  return z
    .object({ deleted: z.number().int() })
    .parse(await api.post<unknown>('/api/artworks/bulk-delete', { artworkIds }))
}

export const favoriteGroupSchema = z.object({
  groupId: z.number().int().positive(),
  name: z.string(),
  artworkCount: z.number().int().nonnegative(),
})
export type FavoriteGroup = z.infer<typeof favoriteGroupSchema>

const favoriteStateSchema = z.object({
  artworkId: z.number().int().positive(),
  isFavorite: z.boolean(),
  groupIds: z.array(z.number().int().positive()),
})

export async function listFavoriteGroups() {
  return z.array(favoriteGroupSchema).parse(await api.get<unknown>('/api/favorite-groups'))
}

export async function createFavoriteGroup(name: string) {
  return favoriteGroupSchema.parse(await api.post<unknown>('/api/favorite-groups', { name }))
}

export async function renameFavoriteGroup(groupId: number, name: string) {
  return favoriteGroupSchema.parse(
    await api.patch<unknown>(`/api/favorite-groups/${String(groupId)}`, { name }),
  )
}

export async function deleteFavoriteGroup(groupId: number) {
  return z
    .object({ deleted: z.number().int() })
    .parse(await api.delete<unknown>(`/api/favorite-groups/${String(groupId)}`))
}

export async function replaceFavoriteState(
  artworkId: number,
  isFavorite: boolean,
  groupIds: number[],
) {
  return favoriteStateSchema.parse(
    await api.put<unknown>(`/api/artworks/${String(artworkId)}/favorite`, {
      isFavorite,
      groupIds,
    }),
  )
}

export async function bulkSetFavorite(artworkIds: number[], isFavorite: boolean) {
  return z
    .object({ updated: z.number().int() })
    .parse(await api.post<unknown>('/api/artworks/bulk-favorite', { artworkIds, isFavorite }))
}

export async function bulkUpdateFavoriteGroups(
  artworkIds: number[],
  addGroupIds: number[],
  removeGroupIds: number[],
) {
  return z.object({ updated: z.number().int() }).parse(
    await api.post<unknown>('/api/artworks/bulk-favorite-groups', {
      artworkIds,
      addGroupIds,
      removeGroupIds,
    }),
  )
}

export async function syncFavorite(artworkId: number) {
  return z
    .object({ isFavorite: z.boolean(), tags: z.array(z.string()) })
    .parse(await api.post<unknown>(`/api/artworks/${String(artworkId)}/favorite/sync`))
}
