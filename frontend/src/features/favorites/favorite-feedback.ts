import { toast } from '@ui/toast'

import type { ArtworkSource } from '../artworks/artwork-source'
import type { FavoriteState } from './favorites-api'

export function notifyFavoriteUpdate(state: FavoriteState, source: ArtworkSource = 'pixiv') {
  const title = state.isFavorite ? '已收藏' : '已取消收藏'
  if (source === 'pixiv' && !state.pixivSynced) {
    toast.warning(`${title}（仅本地）`, {
      description: 'Pixiv 中已找不到该作品，仅更新了本地收藏。',
    })
    return
  }
  toast.success(title)
}
