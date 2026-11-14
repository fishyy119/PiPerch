import { useRoute, useRouter } from 'vue-router'

import { getRandomArtworkId } from '@/features/artworks/artworks-api'

export function useRandomArtwork() {
  const route = useRoute()
  const router = useRouter()

  async function openRandomArtwork() {
    const excludeArtworkId = route.params.artworkId ? Number(route.params.artworkId) : undefined
    const artworkId = await getRandomArtworkId(excludeArtworkId)
    if (artworkId === null) return

    await router.push(`/artworks/${String(artworkId)}`)
    window.scrollTo({ top: 0 })
  }

  return { openRandomArtwork }
}
