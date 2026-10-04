import { z } from 'zod'

import { api } from '@/shared/api/http'

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
