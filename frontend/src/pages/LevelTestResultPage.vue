<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Skeleton from 'primevue/skeleton'
import ErrorBox from '../components/ErrorBox.vue'
import LevelTestResultCard from '../components/LevelTestResultCard.vue'
import { levelTestApi } from '../api/endpoints'
import type { LevelTestResult } from '../api/types'
import { toUiError, type UiError } from '../utils'

// 대시보드 할 일 "확인할 레벨테스트"에서 들어오는 화면 (기획 ADR-0021)

const props = defineProps<{ id: number }>()

const result = ref<LevelTestResult | null>(null)
const error = ref<UiError | null>(null)

async function load() {
  error.value = null
  try {
    result.value = await levelTestApi.result(props.id)
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-md">
    <ErrorBox :error="error" @retry="load" />
    <Skeleton v-if="!result && !error" height="16rem" />
    <LevelTestResultCard v-else-if="result" :result="result" @changed="r => (result = r)" />
  </div>
</template>
