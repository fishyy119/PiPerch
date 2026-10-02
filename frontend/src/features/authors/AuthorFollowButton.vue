<script setup lang="ts">
import { LoaderCircle, UserMinus, UserPlus } from '@lucide/vue'
import { useMutation } from '@tanstack/vue-query'

import { followUser, unfollowUser } from '@/features/authors/author-api'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import { toast } from '@ui/toast'

interface FollowChange {
  userId: number
  followed: boolean
}

const props = withDefaults(
  defineProps<{
    userId: number
    followed: boolean | null
    size?: 'default' | 'small'
  }>(),
  { size: 'default' },
)

const emit = defineEmits<{
  change: [followed: boolean]
}>()

const mutation = useMutation({
  mutationFn: async (change: FollowChange) => {
    if (change.followed) await followUser(change.userId)
    else await unfollowUser(change.userId)
  },
  onSuccess: (_, change) => {
    emit('change', change.followed)
    toast.success(
      change.followed
        ? `已关注作者 ${String(change.userId)}`
        : `已取消关注作者 ${String(change.userId)}`,
    )
  },
  onError: (error, change) => {
    toast.error(change.followed ? '关注作者失败' : '取消关注作者失败', {
      description: errorMessage(error),
    })
  },
})

function toggleFollow() {
  if (props.followed === null) return
  mutation.mutate({ userId: props.userId, followed: !props.followed })
}
</script>

<template>
  <Button
    :variant="followed ? 'secondary' : 'primary'"
    :size="size"
    :disabled="followed === null || mutation.isPending.value"
    @click="toggleFollow"
  >
    <LoaderCircle v-if="mutation.isPending.value" class="animate-spin" :size="17" />
    <UserMinus v-else-if="followed" :size="17" />
    <UserPlus v-else :size="17" />
    {{
      followed === null
        ? '未登录'
        : mutation.isPending.value
          ? mutation.variables.value?.followed
            ? '关注中…'
            : '取消中…'
          : followed
            ? '取消关注'
            : '关注'
    }}
  </Button>
</template>
