<script setup lang="ts">
import { Cookie, ShieldCheck } from '@lucide/vue'
import { useMutation } from '@tanstack/vue-query'
import { computed } from 'vue'

import { validatePixivCookie } from '@/features/settings/settings-api'
import { useSettingField } from '@/features/settings/useSettingField'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Textarea from '@ui/Textarea.vue'
import { toast } from '@ui/toast'

import SettingItem from '../SettingItem.vue'
import SettingsSection from '../SettingsSection.vue'

const cookieField = useSettingField<'pixivCookie', string>('pixivCookie', {
  label: 'Cookie',
  initialValue: '',
  read: (value) => value ?? '',
  write: (value) => value.trim() || null,
})
const cookie = cookieField.value
const configured = computed(() => Boolean(cookieField.savedValue.value))

const validationMutation = useMutation({
  mutationFn: () => validatePixivCookie(cookie.value.trim()),
  onSuccess: (result) => {
    if (result.valid) {
      toast.success('Cookie 验证通过')
      return
    }
    toast.warning('Cookie 无效或已过期')
  },
  onError: (error) => {
    toast.error('Cookie 验证失败', { description: errorMessage(error) })
  },
})
</script>

<template>
  <SettingsSection
    section-id="settings-pixiv"
    title="Pixiv"
    description="配置访问账号收藏与受限内容所需的凭据。"
    :icon="Cookie"
  >
    <SettingItem
      title="Cookie"
      description="粘贴浏览器中的完整 Cookie 字符串；修改后可先验证，再统一保存。"
      control-id="pixiv-cookie"
      layout="expanded"
    >
      <template #status>
        <span
          class="rounded-full px-2.5 py-0.5 text-xs"
          :class="configured ? 'bg-success/15 text-success' : 'bg-warning/15 text-warning'"
        >
          {{ configured ? '已配置' : '未配置' }}
        </span>
      </template>
      <div class="flex items-end gap-3">
        <Textarea
          id="pixiv-cookie"
          v-model="cookie"
          class="min-w-0 flex-1 resize-y font-mono text-xs"
          autocomplete="off"
          placeholder="粘贴完整 Cookie 字符串"
          @blur="cookieField.save"
        />
        <Button
          class="shrink-0"
          variant="secondary"
          size="small"
          :disabled="!cookie.trim() || validationMutation.isPending.value"
          @click="validationMutation.mutate()"
        >
          <ShieldCheck :size="16" />
          {{ validationMutation.isPending.value ? '验证中…' : '验证' }}
        </Button>
      </div>
    </SettingItem>
  </SettingsSection>
</template>
