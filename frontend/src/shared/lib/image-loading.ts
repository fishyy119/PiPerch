import { type QueryClient, useQuery } from '@tanstack/vue-query'
import { useIntersectionObserver, useObjectUrl } from '@vueuse/core'
import { computed, type MaybeRefOrGetter, type Ref, shallowRef, toValue, watch } from 'vue'

const imageQueryKey = ['remote-image'] as const

// 导航只取消已有下载，需要时重试仍在使用且没有成功结果的图片。
export const imageRequests = {
  cancel(queryClient: QueryClient) {
    return queryClient.cancelQueries({ queryKey: imageQueryKey })
  },
  retryUnfinished(queryClient: QueryClient) {
    return queryClient.refetchQueries({
      queryKey: imageQueryKey,
      type: 'active',
      predicate: ({ state }) => state.data === undefined && state.fetchStatus === 'idle',
    })
  },
}

export function useImageSource(
  image: Readonly<Ref<HTMLImageElement | null>>,
  src: MaybeRefOrGetter<string>,
  loading: MaybeRefOrGetter<'eager' | 'lazy' | undefined>,
) {
  const source = computed(() => toValue(src))
  const managed = computed(() => {
    if (source.value === '') return false
    const url = new URL(source.value, window.location.href)
    return url.origin === window.location.origin && url.pathname === '/api/pixiv-images'
  })
  const visible = shallowRef(false)
  // fetch 不受 img 的原生懒加载控制，接近视口后才发起远程图片请求。
  const { stop } = useIntersectionObserver(
    () => (managed.value && toValue(loading) === 'lazy' ? image.value : null),
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      visible.value = true
      stop()
    },
    { rootMargin: '600px' },
  )
  // Vue Query 合并同地址请求，并在最后一个使用者卸载或更换地址时取消下载。
  const query = useQuery({
    queryKey: computed(() => [...imageQueryKey, source.value] as const),
    queryFn: async ({ queryKey, signal }) => {
      const response = await fetch(queryKey[1], { signal })
      if (!response.ok) throw new Error(`图片加载失败：HTTP ${String(response.status)}`)
      return response.blob()
    },
    enabled: computed(
      () =>
        managed.value &&
        (toValue(loading) !== 'lazy' || visible.value || !('IntersectionObserver' in window)),
    ),
    staleTime: Number.POSITIVE_INFINITY,
    // 短时间复用同地址响应，一分钟后回收闲置 Blob。
    gcTime: 60_000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  const objectUrl = useObjectUrl(query.data)
  watch(
    query.error,
    (error) => {
      if (error !== null) image.value?.dispatchEvent(new Event('error'))
    },
    { flush: 'post' },
  )
  return computed(() => {
    const url = managed.value ? objectUrl.value : source.value
    return url === '' ? undefined : url
  })
}
