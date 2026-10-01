<script setup lang="ts">
import { Download } from '@lucide/vue'

import Input from '@ui/Input.vue'
import NumberInput from '@ui/NumberInput.vue'
import Slider from '@ui/Slider.vue'

import SettingItem from '../SettingItem.vue'
import SettingsSection from '../SettingsSection.vue'
import { useSettingField } from '../useSettingField'

const proxyUrlField = useSettingField<'proxyUrl', string>('proxyUrl', {
  label: 'HTTP/HTTPS 代理',
  initialValue: '',
  read: (value) => value ?? '',
  write: (value) => value.trim() || null,
})
const proxyUrl = proxyUrlField.value

const downloadConcurrencyField = useSettingField('downloadConcurrency', {
  label: '媒体并发数',
  initialValue: 3,
})
const downloadConcurrency = downloadConcurrencyField.value

function commitDownloadConcurrency(value: number) {
  downloadConcurrency.value = value
  downloadConcurrencyField.save()
}

const requestIntervalField = useSettingField('requestIntervalMs', {
  label: '元数据请求间隔',
  initialValue: 500,
})
const requestIntervalMs = requestIntervalField.value
</script>

<template>
  <SettingsSection
    section-id="settings-download"
    title="下载与网络"
    description="控制 Pixiv 请求方式和媒体下载节奏。"
    :icon="Download"
  >
    <SettingItem
      title="HTTP/HTTPS 代理"
      description="可选；留空时使用系统的默认网络连接。"
      control-id="proxy-url"
    >
      <Input
        id="proxy-url"
        v-model="proxyUrl"
        placeholder="http://127.0.0.1:7890"
        @blur="proxyUrlField.save"
      />
    </SettingItem>
    <SettingItem title="媒体并发数" description="允许同时下载的媒体数量，范围为 1–8。">
      <div class="flex items-center gap-4">
        <Slider
          v-model="downloadConcurrency"
          class="flex-1"
          :min="1"
          :max="8"
          :step="1"
          @commit="commitDownloadConcurrency"
        />
        <output class="min-w-9 text-right text-sm font-medium tabular-nums">
          {{ downloadConcurrency }}
        </output>
      </div>
    </SettingItem>
    <SettingItem
      title="元数据请求间隔"
      description="连续读取作品信息时的等待时间，单位为毫秒。"
      control-id="request-interval"
    >
      <NumberInput
        id="request-interval"
        v-model="requestIntervalMs"
        :min="0"
        :max="60000"
        required
        @commit="requestIntervalField.save"
      />
    </SettingItem>
  </SettingsSection>
</template>
