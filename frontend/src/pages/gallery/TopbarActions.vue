<template>
  <Teleport defer to="#topbar-actions">
    <div class="flex min-w-0 flex-1 items-center justify-start gap-2">
      <slot />
    </div>
  </Teleport>
</template>
