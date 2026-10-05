const artworkPathPattern = /^\/(?:[a-z]{2}(?:-[a-z]{2})?\/)?artworks\/(\d+)\/?$/iu

function positiveSafeInteger(value: string | null) {
  if (value === null || !/^\d+$/u.test(value)) return null
  const number = Number(value)
  return Number.isSafeInteger(number) && number > 0 ? number : null
}

/**
 * 从 Pixiv 作品链接中提取作品 ID。
 *
 * 支持绝对或相对的现代作品路径，以及带 `illust_id` 的旧式链接；非 HTTP(S)、
 * 非 Pixiv 域名、未知路径或无效作品 ID 均返回 `null`。
 */
export function pixivArtworkIdFromUrl(value: string) {
  let url: URL
  try {
    url = new URL(value, 'https://www.pixiv.net')
  } catch {
    return null
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
  const hostname = url.hostname.toLowerCase()
  if (hostname !== 'pixiv.net' && !hostname.endsWith('.pixiv.net')) return null

  const artworkPathMatch = artworkPathPattern.exec(url.pathname)
  if (artworkPathMatch) return positiveSafeInteger(artworkPathMatch[1] ?? null)

  if (url.pathname.toLowerCase().endsWith('/member_illust.php')) {
    return positiveSafeInteger(url.searchParams.get('illust_id'))
  }
  return null
}
