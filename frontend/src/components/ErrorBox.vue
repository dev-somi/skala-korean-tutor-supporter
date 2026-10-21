<script setup lang="ts">
import Message from 'primevue/message'
import Button from 'primevue/button'
import type { UiError } from '../utils'

// 오류를 "다시 시도하면 될 수 있는 것"과 "복구 불가"로 나눠 보여 준다 (참고노트 2장 #11)
defineProps<{ error: UiError | null }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <Message v-if="error" :severity="error.retryable ? 'warn' : 'error'" class="my-3">
    <div class="flex flex-wrap items-center gap-3">
      <span class="font-semibold">{{ error.retryable ? '일시적인 오류예요.' : '처리할 수 없는 요청이에요.' }}</span>
      <span class="text-sm break-all">{{ error.message }}</span>
      <Button v-if="error.retryable" label="다시 시도" icon="pi pi-refresh" size="small" severity="warn" outlined @click="$emit('retry')" />
    </div>
  </Message>
</template>
