<script setup lang="ts">
import { CheckCircle2, Cookie, Save, ShieldCheck } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { reactive, ref, watch } from 'vue'

import { getSettings, updateSettings, validatePixivCookie } from '@/features/settings/settings-api'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Input from '@ui/Input.vue'
import Textarea from '@ui/Textarea.vue'

const queryClient = useQueryClient()
const notice = ref('')
const form = reactive({
  pixivCookie: '',
  proxyUrl: '',
  libraryRoot: '',
  downloadConcurrency: 3,
  requestIntervalMs: 500,
})

const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: getSettings })
watch(
  () => settingsQuery.data.value,
  (settings) => {
    if (!settings) return
    form.pixivCookie = settings.pixivCookie ?? ''
    form.proxyUrl = settings.proxyUrl ?? ''
    form.libraryRoot = settings.libraryRoot
    form.downloadConcurrency = settings.downloadConcurrency
    form.requestIntervalMs = settings.requestIntervalMs
  },
  { immediate: true },
)

const saveMutation = useMutation({
  mutationFn: () =>
    updateSettings({
      pixivCookie: form.pixivCookie.trim() || null,
      proxyUrl: form.proxyUrl.trim() || null,
      libraryRoot: form.libraryRoot.trim(),
      downloadConcurrency: form.downloadConcurrency,
      requestIntervalMs: form.requestIntervalMs,
    }),
  onMutate: () => {
    notice.value = ''
  },
  onSuccess: async () => {
    notice.value = '设置已保存。'
    await queryClient.invalidateQueries({ queryKey: ['settings'] })
  },
})

const validationMutation = useMutation({
  mutationFn: () => validatePixivCookie(form.pixivCookie.trim()),
  onMutate: () => {
    notice.value = ''
  },
  onSuccess: (result) => {
    notice.value = result.valid ? 'Cookie 验证通过。' : 'Cookie 无效或已过期。'
  },
})
</script>

<template>
  <form class="mx-auto max-w-4xl space-y-6" @submit.prevent="saveMutation.mutate()">
    <Card as="section" class="p-5 md:p-6">
      <div class="mb-5 flex items-start gap-3">
        <span class="grid size-10 place-items-center rounded-xl bg-primary/15 text-primary"
          ><Cookie :size="21"
        /></span>
        <h2 class="font-semibold">Pixiv Cookie</h2>
        <span
          class="ml-auto rounded-full px-3 py-1 text-xs"
          :class="
            settingsQuery.data.value?.pixivCookie
              ? 'bg-success/15 text-success'
              : 'bg-warning/15 text-warning'
          "
        >
          {{ settingsQuery.data.value?.pixivCookie ? '已配置' : '未配置' }}
        </span>
      </div>
      <label class="grid gap-2 text-sm">
        <span>Cookie</span>
        <Textarea
          v-model="form.pixivCookie"
          class="resize-y font-mono text-xs"
          autocomplete="off"
          placeholder="粘贴完整 Cookie 字符串"
        />
      </label>
      <div class="mt-3 flex flex-wrap gap-2">
        <Button
          variant="secondary"
          :disabled="!form.pixivCookie.trim() || validationMutation.isPending.value"
          @click="validationMutation.mutate()"
          ><ShieldCheck :size="17" />验证</Button
        >
      </div>
    </Card>

    <Card as="section" class="p-5 md:p-6">
      <h2 class="font-semibold">下载与存储</h2>
      <div class="mt-5 grid gap-5 md:grid-cols-2">
        <label class="grid gap-2 text-sm md:col-span-2">
          <span>图库根目录</span>
          <Input v-model="form.libraryRoot" required />
        </label>
        <label class="grid gap-2 text-sm md:col-span-2">
          <span>HTTP/HTTPS 代理（可选）</span>
          <Input v-model="form.proxyUrl" placeholder="http://127.0.0.1:7890" />
        </label>
        <label class="grid gap-2 text-sm">
          <span>媒体并发数（1–8）</span>
          <Input v-model.number="form.downloadConcurrency" type="number" min="1" max="8" required />
        </label>
        <label class="grid gap-2 text-sm">
          <span>元数据请求间隔（毫秒）</span>
          <Input
            v-model.number="form.requestIntervalMs"
            type="number"
            min="0"
            max="60000"
            required
          />
        </label>
      </div>
      <Button class="mt-5" type="submit" :disabled="saveMutation.isPending.value"
        ><Save :size="17" />{{ saveMutation.isPending.value ? '保存中…' : '保存设置' }}</Button
      >
    </Card>

    <div
      v-if="notice"
      class="flex items-center gap-2 rounded-xl bg-success/12 p-4 text-sm text-success"
    >
      <CheckCircle2 :size="18" />{{ notice }}
    </div>
    <p
      v-if="saveMutation.error.value || validationMutation.error.value"
      class="rounded-xl bg-destructive/12 p-4 text-sm text-destructive"
    >
      {{ errorMessage(saveMutation.error.value ?? validationMutation.error.value) }}
    </p>
  </form>
</template>
