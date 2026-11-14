<script setup lang="ts">
import DOMPurify from 'dompurify'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import type { ArtworkLink } from '@/features/artworks/artworks-api'
import { useDownloadWorkspaceStore } from '@/features/downloads/download-workspace'

const props = defineProps<{
  html: string
  links: Record<string, ArtworkLink>
}>()
const router = useRouter()
const { requestPreview } = useDownloadWorkspaceStore()
const clean = computed(() => {
  const sanitized = DOMPurify.sanitize(props.html)
  const document = new DOMParser().parseFromString(sanitized, 'text/html')
  document.querySelectorAll<HTMLAnchorElement>('a').forEach((anchor) => {
    // 站内跳转标记，保护性清除同名属性。
    anchor.removeAttribute('data-local-artwork-id')
    anchor.removeAttribute('data-pixiv-artwork-id')

    const href = anchor.getAttribute('href')
    if (href === null) return

    const link = props.links[href]
    const localId = link?.localArtworkId
    if (typeof localId === 'number') {
      anchor.href = `/artworks/${String(localId)}`
      anchor.dataset.localArtworkId = String(localId)
      anchor.removeAttribute('target')
      return
    }
    if (link?.source === 'pixiv') anchor.dataset.pixivArtworkId = String(link.remoteId)

    // 严格限制外链行为
    anchor.target = '_blank'
    anchor.relList.add('noreferrer')
  })
  return document.body.innerHTML
})

function navigateToArtwork(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0) return
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return // 对应打开新标签页等行为，自动由浏览器操作
  if (!(event.target instanceof Element)) return

  const anchor = event.target.closest<HTMLAnchorElement>('a')
  const artworkId = anchor?.dataset.localArtworkId
  const pixivId = anchor?.dataset.pixivArtworkId
  if (!artworkId && !pixivId) return

  event.preventDefault()
  // 复用SPA的站内导航，避免重复页面加载
  if (artworkId) {
    void router.push(`/artworks/${artworkId}`)
    return
  }
  if (pixivId) {
    requestPreview({ sourceType: 'artwork', inputs: [pixivId], page: 0 })
    void router.push('/downloads')
  }
}
</script>

<template>
  <!-- 作品简介经 DOMPurify 清理后才允许渲染。 -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="safe-description" @click="navigateToArtwork" v-html="clean" />
</template>

<style scoped>
.safe-description :deep(a) {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 0.15rem;
}

.safe-description :deep(p) {
  margin-block: 0.5rem;
}
</style>
