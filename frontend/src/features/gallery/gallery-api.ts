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
  groupIds: z.array(z.number().int().positive()),
})
export type ArtworkSummary = z.infer<typeof artworkSummarySchema>

const artworkPageSchema = z.object({
  items: z.array(artworkSummarySchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})

const namedCountSchema = z.object({
  itemId: z.number().int().positive(),
  name: z.string(),
  count: z.number().int(),
  subtitle: z.string().nullable(),
})
const namedCountPageSchema = z.object({
  items: z.array(namedCountSchema),
  page: z.number().int(),
  size: z.number().int(),
  totalElements: z.number().int(),
  totalPages: z.number().int(),
})
export type NamedCount = z.infer<typeof namedCountSchema>

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
  groupIds: number[]
  sort: string
  order: string
  randomSeed?: number
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
  filters.groupIds.forEach((id) => params.append('groupId', String(id)))
  if (filters.authorId !== undefined) params.set('authorId', String(filters.authorId))
  if (filters.seriesId !== undefined) params.set('seriesId', String(filters.seriesId))
  if (filters.artworkType) params.set('artworkType', filters.artworkType)
  if (filters.randomSeed !== undefined) params.set('randomSeed', String(filters.randomSeed))
  return params
}

export async function listArtworks(filters: GalleryFilters) {
  return artworkPageSchema.parse(
    await api.get<unknown>(`/api/artworks?${galleryQuery(filters).toString()}`),
  )
}

export async function listTags(search = '', includeIds: number[] = []) {
  const params = new URLSearchParams({ search, limit: '100' })
  includeIds.forEach((id) => params.append('includeId', String(id)))
  return z.array(tagSchema).parse(await api.get<unknown>(`/api/tags?${params.toString()}`))
}

export async function listAuthors(search: string, includeIds: number[] = []) {
  const params = new URLSearchParams({ search, limit: '100' })
  includeIds.forEach((id) => params.append('includeId', String(id)))
  return z
    .array(namedCountSchema)
    .parse(await api.get<unknown>(`/api/authors?${params.toString()}`))
}

export async function listSeries(page: number, search: string) {
  const params = new URLSearchParams({ page: String(page), search })
  return namedCountPageSchema.parse(await api.get<unknown>(`/api/series?${params.toString()}`))
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

export const artworkGroupSchema = z.object({
  groupId: z.number().int().positive(),
  name: z.string(),
  artworkCount: z.number().int().nonnegative(),
})
export type ArtworkGroup = z.infer<typeof artworkGroupSchema>

const favoriteStateSchema = z.object({
  artworkId: z.number().int().positive(),
  isFavorite: z.boolean(),
})

const favoriteSyncPlanSchema = z.object({
  planId: z.string(),
  pixivFavoriteCount: z.number().int().nonnegative(),
  localArtworkCount: z.number().int().nonnegative(),
  localFavoriteCount: z.number().int().nonnegative(),
  matchedFavoriteCount: z.number().int().nonnegative(),
  unavailableLocallyCount: z.number().int().nonnegative(),
  addCount: z.number().int().nonnegative(),
  removeCount: z.number().int().nonnegative(),
})
export type FavoriteSyncPlan = z.infer<typeof favoriteSyncPlanSchema>

const favoriteSyncResultSchema = z.object({
  added: z.number().int().nonnegative(),
  removed: z.number().int().nonnegative(),
})

const artworkGroupsSchema = z.object({
  artworkId: z.number().int().positive(),
  groupIds: z.array(z.number().int().positive()),
})

export async function listGroups() {
  return z.array(artworkGroupSchema).parse(await api.get<unknown>('/api/groups'))
}

export async function createGroup(name: string) {
  return artworkGroupSchema.parse(await api.post<unknown>('/api/groups', { name }))
}

export async function renameGroup(groupId: number, name: string) {
  return artworkGroupSchema.parse(
    await api.patch<unknown>(`/api/groups/${String(groupId)}`, { name }),
  )
}

export async function deleteGroup(groupId: number) {
  return z
    .object({ deleted: z.number().int() })
    .parse(await api.delete<unknown>(`/api/groups/${String(groupId)}`))
}

export async function replaceFavoriteState(artworkId: number, isFavorite: boolean) {
  return favoriteStateSchema.parse(
    await api.put<unknown>(`/api/artworks/${String(artworkId)}/favorite`, {
      isFavorite,
    }),
  )
}

export async function createFavoriteSyncPlan() {
  return favoriteSyncPlanSchema.parse(await api.post<unknown>('/api/favorite-sync-plans'))
}

export async function applyFavoriteSyncPlan(planId: string) {
  return favoriteSyncResultSchema.parse(
    await api.post<unknown>(`/api/favorite-sync-plans/${encodeURIComponent(planId)}/apply`),
  )
}

export async function replaceArtworkGroups(artworkId: number, groupIds: number[]) {
  return artworkGroupsSchema.parse(
    await api.put<unknown>(`/api/artworks/${String(artworkId)}/groups`, { groupIds }),
  )
}

export async function bulkUpdateArtworkGroups(
  artworkIds: number[],
  addGroupIds: number[],
  removeGroupIds: number[],
) {
  await api.patch<undefined>('/api/artworks/groups', { artworkIds, addGroupIds, removeGroupIds })
}
