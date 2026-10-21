<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ErrorBox from './ErrorBox.vue'
import { levelTestApi, studentsApi } from '../api/endpoints'
import { STANDARD_LEVELS, levelName, type LevelTestResult, type StudentSummary } from '../api/types'
import { formatDateTime, toUiError, type UiError } from '../utils'

// 저장한 레벨테스트 결과를 선생님이 확인하는 카드 (기획 ADR-0021).
// 추천 등급은 저장할 때 코드가 정했다. 학생 카드에는 여기서 [반영]을 눌러야 들어간다.

const props = defineProps<{ result: LevelTestResult }>()
const emit = defineEmits<{ changed: [result: LevelTestResult] }>()

const router = useRouter()
const toast = useToast()

const level = ref<number | null>(props.result.suggestedLevel)
const studentId = ref<number | null>(null)
const students = ref<StudentSummary[]>([])
const busy = ref(false)
const error = ref<UiError | null>(null)

const pending = computed(() => props.result.status === 'pending')
const levelOptions = STANDARD_LEVELS.map(n => ({ value: n, label: levelName(n) }))
const studentOptions = computed(() => students.value.map(s => ({ value: s.id, label: `${s.name} · ${levelName(s.standardLevel)}` })))
const appliedTo = computed(() => students.value.find(s => s.id === props.result.studentId)?.name)

onMounted(async () => {
  try {
    students.value = await studentsApi.list()
  } catch (e) {
    error.value = toUiError(e)
  }
})

async function run(action: () => Promise<LevelTestResult>, done: string) {
  busy.value = true
  error.value = null
  try {
    const updated = await action()
    toast.add({ severity: 'success', summary: done, life: 2500 })
    emit('changed', updated)
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    busy.value = false
  }
}

const applyToStudent = () =>
  run(() => levelTestApi.apply(props.result.id, studentId.value!, level.value!), `${levelName(level.value)}으로 학생 카드에 반영했어요`)
const dismiss = () => run(() => levelTestApi.dismiss(props.result.id), '결과를 버렸어요')

/** 새 학생 등록 화면으로. 등록을 저장하면 그 화면이 이 결과를 새 학생에 반영한다 */
function registerNew() {
  const takenOn = new Date(props.result.takenAt).toLocaleDateString('sv-SE') // YYYY-MM-DD (로컬 날짜)
  router.push({
    path: '/students/new',
    query: { result: String(props.result.id), level: String(level.value), assessedOn: takenOn, note: props.result.note || undefined },
  })
}
</script>

<template>
  <section class="rounded-xl border border-surface-200 bg-white p-4">
    <div class="mb-1 flex flex-wrap items-center gap-2">
      <h2 class="m-0 text-base font-bold">레벨테스트 결과</h2>
      <Tag v-if="result.status === 'pending'" value="확인 대기" severity="warn" />
      <Tag v-else-if="result.status === 'applied'" value="반영함" severity="success" />
      <Tag v-else value="버림" severity="secondary" />
      <span class="text-xs text-surface-400">{{ formatDateTime(result.takenAt) }} · {{ result.answered }}문항 확인</span>
    </div>

    <div class="text-2xl font-bold" :class="result.suggestedLevel == null ? 'text-surface-400' : 'text-primary-600'">
      {{ result.suggestedLevel == null ? '추천 등급 없음' : levelName(result.suggestedLevel) }}
    </div>
    <p class="mb-2 mt-1 text-sm text-surface-600">{{ result.score.reason }}</p>
    <ul class="m-0 mb-3 list-none space-y-1 p-0 text-sm text-surface-600">
      <li v-if="result.score.hangul_correct != null">한글 읽기 {{ result.score.hangul_correct }}개 맞음</li>
      <li v-for="l in result.score.levels.filter(l => l.status !== 'untested')" :key="l.level">{{ levelName(l.level) }} {{ l.correct }}/{{ l.answered }}</li>
    </ul>
    <p v-if="result.note" class="mb-3 mt-0 rounded-lg bg-surface-50 p-2 text-sm">{{ result.note }}</p>

    <ErrorBox :error="error" />

    <template v-if="pending">
      <label class="mb-1 block text-sm font-semibold text-surface-600" for="ltr-level">반영할 등급 (추천과 다르게 골라도 돼요)</label>
      <Select id="ltr-level" v-model="level" :options="levelOptions" option-label="label" option-value="value" placeholder="등급을 고르세요" class="mb-3 w-full" />

      <Button label="새 학생으로 등록" icon="pi pi-user-plus" class="mb-3 w-full" :disabled="level == null || busy" @click="registerNew" />

      <label class="mb-1 block text-sm font-semibold text-surface-600" for="ltr-student">이미 등록한 학생이면</label>
      <div class="mb-3 flex gap-2">
        <Select id="ltr-student" v-model="studentId" :options="studentOptions" option-label="label" option-value="value" placeholder="학생 고르기" filter class="min-w-0 flex-1" />
        <Button label="반영" severity="secondary" :disabled="level == null || studentId == null" :loading="busy" @click="applyToStudent" />
      </div>
      <Button label="반영하지 않고 버리기" icon="pi pi-trash" severity="secondary" text size="small" :disabled="busy" @click="dismiss" />
    </template>
    <Message v-else-if="result.status === 'applied'" severity="success">
      <RouterLink v-if="result.studentId" :to="`/students/${result.studentId}`">{{ appliedTo ?? '학생' }}</RouterLink>
      카드에 {{ levelName(result.appliedLevel) }}으로 반영했어요.
    </Message>
  </section>
</template>
