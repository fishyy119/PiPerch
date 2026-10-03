const GALLERY_NAVIGATION_STATE_KEY = 'piperchGalleryNavigation'

export interface GalleryNavigationState {
  artworkIds: number[]
}

export function galleryNavigationRouteState(artworkIds: readonly number[]) {
  return {
    [GALLERY_NAVIGATION_STATE_KEY]: {
      artworkIds: [...artworkIds],
    },
  }
}

export function parseGalleryNavigationState(state: unknown): GalleryNavigationState | null {
  if (typeof state !== 'object' || state === null) return null

  const value = (state as Record<string, unknown>)[GALLERY_NAVIGATION_STATE_KEY]
  if (typeof value !== 'object' || value === null) return null

  const candidateArtworkIds = (value as Record<string, unknown>).artworkIds
  if (!Array.isArray(candidateArtworkIds) || candidateArtworkIds.length === 0) return null

  const artworkIds: number[] = []
  for (const artworkId of candidateArtworkIds as unknown[]) {
    if (typeof artworkId !== 'number' || !Number.isSafeInteger(artworkId) || artworkId <= 0) {
      return null
    }
    artworkIds.push(artworkId)
  }

  return { artworkIds }
}
