<script setup lang="ts">
import ProgressSpinner from 'primevue/progressspinner'
import type { ProgressEvent } from '../api/types'

// SSE node_finished 이벤트를 단계 목록으로 보여 준다
defineProps<{ steps: ProgressEvent[]; running: boolean; title?: string; hint?: string }>()
</script>

<template>
  <div class="rounded-xl border border-surface-200 bg-white p-4">
    <div class="mb-2 flex items-center gap-2">
      <ProgressSpinner v-if="running" style="width: 1.25rem; height: 1.25rem" stroke-width="6" />
      <i v-else class="pi pi-check-circle text-primary-600" />
      <span class="font-semibold">{{ title ?? 'AI 작업 진행 상황' }}</span>
    </div>
    <p v-if="hint && running" class="mb-2 text-sm text-surface-500">{{ hint }}</p>
    <ol class="m-0 flex list-none flex-wrap gap-2 p-0">
      <li v-for="(step, i) in steps" :key="i" class="rounded-full bg-primary-50 px-3 py-1 text-sm text-primary-800">
        <i class="pi pi-check mr-1 text-xs" />{{ step.label }}
      </li>
      <li v-if="running" class="rounded-full bg-surface-100 px-3 py-1 text-sm text-surface-500">
        <i class="pi pi-spin pi-spinner mr-1 text-xs" />다음 단계 진행 중…
      </li>
    </ol>
  </div>
</template>
