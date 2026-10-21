<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import StudentCard from '../components/StudentCard.vue'
import ErrorBox from '../components/ErrorBox.vue'
import { studentsApi } from '../api/endpoints'
import { LANG_NAMES, PERSONA_NAMES, type Lang, type Persona, type StudentSummary } from '../api/types'
import { toUiError, type UiError } from '../utils'

// 학생 목록. 이름 검색과 상태·모국어·학습 목적 필터는 화면에서만 거른다 (학생 수가 적어서 목록을 한 번에 받는다).

const students = ref<StudentSummary[] | null>(null)
const error = ref<UiError | null>(null)
const query = ref('')
const status = ref<'all' | 'active' | 'paused'>('all')
const lang = ref<Lang | null>(null)
const persona = ref<Persona | null>(null)

async function load() {
  error.value = null
  try {
    students.value = await studentsApi.list()
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

const filtered = computed(() => {
  const q = query.value.trim()
  return (students.value ?? []).filter(s =>
    (!q || s.name.includes(q))
    && (status.value === 'all' || (status.value === 'paused') === (s.status === 'paused'))
    && (!lang.value || s.nativeLanguage === lang.value)
    && (!persona.value || s.persona === persona.value))
})

const statusOptions = [
  { label: '전체', value: 'all' },
  { label: '수업 중', value: 'active' },
  { label: '쉬는 중', value: 'paused' },
]
const langOptions = Object.entries(LANG_NAMES).map(([value, label]) => ({ label, value }))
const personaOptions = Object.entries(PERSONA_NAMES).map(([value, label]) => ({ label, value }))
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <h1 class="m-0 text-xl font-bold">학생</h1>
    <span v-if="students" class="text-sm text-surface-500">{{ filtered.length }} / {{ students.length }}명</span>
    <div class="flex-1" />
    <RouterLink to="/students/new"><Button label="학생 등록" icon="pi pi-user-plus" size="small" /></RouterLink>
  </div>
  <p class="mb-4 mt-0 text-sm text-surface-500">카드를 누르면 학생 상세로 가요. 상세에서 [정보 수정]으로 프로필을 고칠 수 있어요.</p>

  <div class="mb-4 flex flex-wrap gap-2">
    <InputText v-model="query" placeholder="이름 검색" class="w-full sm:w-48" />
    <Select v-model="status" :options="statusOptions" option-label="label" option-value="value" class="w-32" />
    <Select v-model="lang" :options="langOptions" option-label="label" option-value="value" placeholder="모국어" show-clear class="w-32" />
    <Select v-model="persona" :options="personaOptions" option-label="label" option-value="value" placeholder="학습 목적" show-clear class="w-48" />
  </div>

  <ErrorBox :error="error" @retry="load" />
  <div v-if="!students && !error" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><Skeleton v-for="i in 6" :key="i" height="8rem" /></div>
  <p v-else-if="students && !students.length" class="text-surface-500">아직 학생이 없어요. [학생 등록]을 누르거나 채팅에 학생 설명을 써 보세요.</p>
  <p v-else-if="students && !filtered.length" class="text-surface-500">조건에 맞는 학생이 없어요.</p>
  <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
    <StudentCard v-for="s in filtered" :key="s.id" :student="s" />
  </div>
</template>
