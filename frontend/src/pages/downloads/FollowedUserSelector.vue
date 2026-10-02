<script setup lang="ts">
import { UserRound } from '@lucide/vue'
import { ref } from 'vue'

import type { FollowedUser } from '@/features/discovery/discovery-api'

defineProps<{
  users: readonly FollowedUser[]
  selectedUserId: number | null
}>()

const emit = defineEmits<{
  select: [user: FollowedUser]
}>()

const failedAvatars = ref(new Set<number>())

function markAvatarUnavailable(userId: number) {
  failedAvatars.value = new Set([...failedAvatars.value, userId])
}
</script>

<template>
  <div
    v-if="users.length"
    class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,13rem),1fr))] gap-2.5"
  >
    <button
      v-for="user in users"
      :key="user.userId"
      type="button"
      class="flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border p-2.5 text-left transition hover:border-primary/50 hover:bg-accent"
      :class="selectedUserId === user.userId ? 'border-primary bg-accent ring-1 ring-primary' : ''"
      @click="emit('select', user)"
    >
      <span
        class="grid size-11 shrink-0 place-items-center overflow-hidden rounded-full bg-muted text-muted-foreground"
      >
        <img
          v-if="user.avatarUrl && !failedAvatars.has(user.userId)"
          class="size-full object-cover"
          :src="user.avatarUrl"
          alt=""
          loading="lazy"
          @error="markAvatarUnavailable(user.userId)"
        />
        <UserRound v-else :size="20" />
      </span>
      <strong class="min-w-0 truncate text-sm">{{ user.name }}</strong>
    </button>
  </div>
  <p v-else class="py-5 text-center text-sm text-muted-foreground">当前账号没有已关注作者。</p>
</template>
