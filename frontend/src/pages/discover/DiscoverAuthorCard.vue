<script setup lang="ts">
import { Check, LoaderCircle, UserPlus, UserRound } from '@lucide/vue'
import { ref } from 'vue'

import DiscoveryArtworkCard from '@/features/discovery/DiscoveryArtworkCard.vue'
import type { DiscoveryItem, RecommendedUser } from '@/features/downloads/download-api'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import { toast } from '@ui/toast'

defineProps<{
  author: RecommendedUser
  selectedIds: readonly number[]
  following: boolean
}>()

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
  follow: [userId: number]
}>()

const avatarFailed = ref(false)

function pixivUserUrl(userId: number) {
  return `https://www.pixiv.net/users/${String(userId)}`
}

async function copyUserId(userId: number) {
  try {
    await navigator.clipboard.writeText(String(userId))
    toast.success(`已复制作者 ID ${String(userId)}`)
  } catch (error) {
    toast.error('复制作者 ID 失败', { description: errorMessage(error) })
  }
}
</script>

<template>
  <Card as="article" class="flex h-full flex-col p-4 sm:p-5">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex min-w-0 flex-1 items-center gap-3">
        <div
          class="grid size-14 shrink-0 place-items-center overflow-hidden rounded-full bg-muted text-muted-foreground"
        >
          <img
            v-if="author.avatarUrl && !avatarFailed"
            class="size-full object-cover"
            :src="author.avatarUrl"
            alt=""
            loading="lazy"
            @error="avatarFailed = true"
          />
          <UserRound v-else :size="24" />
        </div>

        <div class="min-w-0">
          <a
            class="block max-w-full cursor-pointer truncate font-semibold transition-colors hover:text-primary"
            :href="pixivUserUrl(author.userId)"
            target="_blank"
            rel="noreferrer"
          >
            {{ author.name }}
          </a>
          <button
            type="button"
            class="app-muted mt-0.5 cursor-pointer text-xs transition-colors hover:text-primary"
            title="复制作者 ID"
            @click="copyUserId(author.userId)"
          >
            ID: {{ author.userId }}
          </button>
        </div>
      </div>

      <Button
        :variant="author.isFollowed ? 'secondary' : 'primary'"
        :disabled="author.isFollowed || following"
        @click="emit('follow', author.userId)"
      >
        <LoaderCircle v-if="following" class="animate-spin" :size="17" />
        <Check v-else-if="author.isFollowed" :size="17" />
        <UserPlus v-else :size="17" />
        {{ following ? '关注中…' : author.isFollowed ? '已关注' : '关注' }}
      </Button>
    </header>

    <p v-if="author.comment" class="app-muted mt-4 line-clamp-2 text-sm whitespace-pre-line">
      {{ author.comment }}
    </p>

    <div v-if="author.artworks.length" class="mt-auto grid grid-cols-5 gap-x-3 gap-y-5 pt-5">
      <DiscoveryArtworkCard
        v-for="artwork in author.artworks"
        :key="artwork.artworkId"
        :artwork="artwork"
        :selected="selectedIds.includes(artwork.artworkId)"
        :show-author="false"
        @toggle="emit('toggle', $event)"
      />
    </div>
    <p v-else class="app-muted mt-auto rounded-xl bg-muted/50 py-8 text-center text-sm">
      当前没有可展示的近期插画。
    </p>
  </Card>
</template>
