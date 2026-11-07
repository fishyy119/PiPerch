const GALLERY_NAVIGATION_STATE_KEY = 'piperchGalleryNavigation'

export interface GalleryNavigationState {
  localArtworkIds: number[]
}

export function galleryNavigationRouteState(localArtworkIds: readonly number[]) {
  return {
    [GALLERY_NAVIGATION_STATE_KEY]: {
      localArtworkIds: [...localArtworkIds],
    },
  }
}

export function parseGalleryNavigationState(state: unknown): GalleryNavigationState | null {
  if (typeof state !== 'object' || state === null) return null

  const value = (state as Record<string, unknown>)[GALLERY_NAVIGATION_STATE_KEY]
  if (typeof value !== 'object' || value === null) return null

  const candidateArtworkIds = (value as Record<string, unknown>).localArtworkIds
  if (!Array.isArray(candidateArtworkIds) || candidateArtworkIds.length === 0) return null

  const localArtworkIds: number[] = []
  for (const localArtworkId of candidateArtworkIds as unknown[]) {
    if (
      typeof localArtworkId !== 'number' ||
      !Number.isSafeInteger(localArtworkId) ||
      localArtworkId <= 0
    ) {
      return null
    }
    localArtworkIds.push(localArtworkId)
  }

  return { localArtworkIds }
}
