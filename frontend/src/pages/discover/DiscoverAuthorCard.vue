<script setup lang="ts">
import { UserRound } from '@lucide/vue'
import { ref } from 'vue'

import type { DiscoveryItem, RecommendedUser } from '@/features/discovery/discovery-api'
import AuthorFollowButton from '@/shared/components/authors/AuthorFollowButton.vue'
import AuthorIdButton from '@/shared/components/authors/AuthorIdButton.vue'
import DiscoveryArtworkCard from '@/shared/components/discovery/DiscoveryArtworkCard.vue'
import Card from '@ui/Card.vue'

defineProps<{
  author: RecommendedUser
  selectedIds: readonly number[]
}>()

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
  followChange: [userId: number, followed: boolean]
}>()

const avatarFailed = ref(false)

function pixivUserUrl(userId: number) {
  return `https://www.pixiv.net/users/${String(userId)}`
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
          <AuthorIdButton class="mt-0.5" :user-id="author.userId" />
        </div>
      </div>

      <AuthorFollowButton
        :user-id="author.userId"
        :followed="author.isFollowed"
        @change="emit('followChange', author.userId, $event)"
      />
    </header>

    <p
      v-if="author.comment"
      class="mt-4 line-clamp-2 text-sm whitespace-pre-line text-muted-foreground"
    >
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
    <p v-else class="mt-auto rounded-xl bg-muted/50 py-8 text-center text-sm text-muted-foreground">
      当前没有可展示的近期插画。
    </p>
  </Card>
</template>
