<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ProgressSteps from '../components/ProgressSteps.vue'
import BriefingPanel from '../components/BriefingPanel.vue'
import LessonFrame from '../components/LessonFrame.vue'
import CategoryReviewCard from '../components/CategoryReviewCard.vue'
import ErrorBox from '../components/ErrorBox.vue'
import { lessonsApi, studentsApi } from '../api/endpoints'
import {
  CATEGORIES, LANG_NAMES, PERSONA_NAMES, levelName, type Category, type Decision, type LessonView, type ProgressEvent, type ReviewPayload, type StudentDetail,
} from '../api/types'
import { toUiError, type UiError } from '../utils'

const props = defineProps<{ id: number }>()
const toast = useToast()

type Phase = 'loading' | 'running' | 'review' | 'done' | 'stale'
const phase = ref<Phase>('loading')
const lesson = ref<LessonView | null>(null)
const student = ref<StudentDetail | null>(null)
const steps = ref<ProgressEvent[]>([])
const payload = ref<ReviewPayload | null>(null)
const decisions = ref<Partial<Record<Category, Decision>>>({})
const error = ref<UiError | null>(null)
let abort: AbortController | null = null
let lastAction: () => void = () => {}

onBeforeUnmount(() => abort?.abort())

async function loadLesson() {
  lesson.value = await lessonsApi.get(props.id)
}

async function init() {
  error.value = null
  try {
    await loadLesson()
    const l = lesson.value!
    // 누구를 위한 준비인지 위에 요약해 둔다. 실패해도 준비 화면은 쓸 수 있게 오류는 무시한다
    studentsApi.get(l.studentId).then(s => (student.value = s)).catch(() => {})
    if (l.status !== 'planned') {
      phase.value = 'done'
    } else if (!l.prepThreadId) {
      start() // 아직 준비를 시작하지 않은 수업: 바로 시작
    } else {
      const state = await lessonsApi.prepState(props.id)
      if (state.status === 'review_required') showReview(state as ReviewPayload)
      else if (state.status === 'done') {
        await loadLesson()
        phase.value = 'done'
      } else phase.value = 'stale' // 연결이 끊겨 멈춘 실행
    }
  } catch (e) {
    error.value = toUiError(e)
    lastAction = init
  }
}
onMounted(init)

function showReview(p: ReviewPayload) {
  payload.value = p
  const next: Partial<Record<Category, Decision>> = {}
  for (const c of CATEGORIES) if (!p.approved_categories.includes(c)) next[c] = { action: 'approve' }
  decisions.value = next
  phase.value = 'review'
}

function onEvent(event: string, data: any) {
  if (event === 'node_finished') steps.value.push(data)
  else if (event === 'review_required') showReview(data)
  else if (event === 'done') {
    loadLesson().then(() => {
      phase.value = 'done'
      toast.add({ severity: 'success', summary: '수업안을 확정했어요', life: 3000 })
    })
  } else if (event === 'error') {
    error.value = { message: data.message, retryable: data.retryable }
  }
}

async function run(task: (signal: AbortSignal) => Promise<void>, retry: () => void) {
  abort?.abort()
  abort = new AbortController()
  error.value = null
  steps.value = []
  phase.value = 'running'
  lastAction = retry
  try {
    await task(abort.signal)
  } catch (e) {
    if ((e as Error).name !== 'AbortError') error.value = toUiError(e)
  }
  // 스트림이 결과 없이 끝났으면(오류 등) 다시 시도할 수 있게 둔다
  if (phase.value === 'running') phase.value = payload.value ? 'review' : 'stale'
}

function start() {
  payload.value = null
  run(signal => lessonsApi.startPrep(props.id, onEvent, signal), start)
}

const pending = computed(() => CATEGORIES.filter(c => decisions.value[c]))
const missingFeedback = computed(() => pending.value.filter(c => decisions.value[c]!.action === 'feedback' && !decisions.value[c]!.feedback?.trim()))

function submit() {
  const body = { ...decisions.value }
  run(signal => lessonsApi.review(props.id, body, onEvent, signal), submit)
}

const codeChecks = computed(() => payload.value?.review_result?.checks.filter(c => c.kind !== 'llm') ?? [])
const adviceChecks = computed(() => payload.value?.review_result?.checks.filter(c => c.kind === 'llm') ?? [])
const adviceFailed = computed(() => adviceChecks.value.filter(c => !c.passed))

const activeWeaknesses = computed(() => student.value?.weaknesses.filter(w => !w.resolved).map(w => w.description) ?? [])

const willRegenerate = computed(() => pending.value.some(c => decisions.value[c]!.action === 'feedback'))
</script>

<template>
  <div v-if="lesson" class="mb-4 flex flex-wrap items-center gap-2">
    <RouterLink to="/prep" class="text-sm">← 수업 준비</RouterLink>
    <h1 class="m-0 w-full text-xl font-bold">
      <RouterLink :to="`/students/${lesson.studentId}`" class="text-inherit">{{ lesson.studentName }}</RouterLink> {{ lesson.lessonNo }}회차 수업 준비
      <span class="text-base font-normal text-surface-500">· {{ lesson.unitNo }}과 · {{ lesson.minutes }}분 · {{ LANG_NAMES[lesson.targetLang] }} 설명</span>
    </h1>
    <!-- 학생 요약 한 줄: 이 준비가 누구를 위한 것인지 (기술 ADR-0029) -->
    <div v-if="student" class="flex w-full flex-wrap items-center gap-2 rounded-lg bg-surface-100 px-3 py-2 text-sm">
      <Tag :value="LANG_NAMES[student.nativeLanguage]" severity="secondary" />
      <span class="font-semibold">{{ levelName(student.standardLevel) }}</span>
      <span v-if="student.persona" class="text-surface-600">· {{ PERSONA_NAMES[student.persona] }}</span>
      <span v-if="student.interests.length" class="text-surface-600">· 관심사 {{ student.interests.slice(0, 3).join(', ') }}</span>
      <span v-if="activeWeaknesses.length" class="text-orange-700">· 약점 {{ activeWeaknesses.slice(0, 3).join(', ') }}</span>
    </div>
  </div>

  <ErrorBox :error="error" @retry="lastAction()" />

  <template v-if="phase === 'running'">
    <ProgressSteps :steps="steps" running title="AI가 수업안을 만들고 있어요" hint="구성안 → 설명 → 대본 → 자동 검토 → 브리핑(지침서 근거) 순서로 진행돼요. 로컬 모델이라 몇 분 걸려요. 이 화면을 떠나면 중단돼요." />
  </template>

  <template v-else-if="phase === 'stale'">
    <Message severity="warn">이전 준비가 중간에 끊겼어요. 처음부터 다시 만들어요.</Message>
    <Button label="수업 준비 다시 시작" icon="pi pi-refresh" class="mt-3" @click="start" />
  </template>

  <template v-else-if="phase === 'review' && payload">
    <Message v-if="payload.review_warning" severity="warn" class="mb-4">
      구성안 점검(교재 ID, 복습, 시간 합계)에서 문제가 있어요. 아래 내용을 꼭 확인해 주세요.
    </Message>
    <details v-if="payload.review_result" class="mb-4 rounded-xl border border-surface-200 bg-white p-3 text-sm">
      <summary class="cursor-pointer font-semibold">
        자동 검토 결과
        <Tag :value="payload.review_result.passed ? '구성안 점검 통과' : '확인 필요'" :severity="payload.review_result.passed ? 'success' : 'warn'" class="ml-1" />
        <Tag v-if="adviceFailed.length" :value="`AI 참고 의견 ${adviceFailed.length}개`" severity="secondary" class="ml-1" />
      </summary>
      <ul class="mb-0 mt-2 space-y-1 pl-5">
        <li v-for="c in codeChecks" :key="c.name">
          <i :class="c.passed ? 'pi pi-check text-primary-600' : 'pi pi-times text-red-500'" class="mr-1 text-xs" /><b>{{ c.name }}</b> — {{ c.reason }}
        </li>
      </ul>
      <template v-if="adviceChecks.length">
        <p class="mb-1 mt-3 text-xs text-surface-500">AI 참고 의견 — 로컬 모델의 판정이라 틀릴 수 있어요. 다시 만들지 않고 보여 주기만 해요.</p>
        <ul class="m-0 space-y-1 pl-5 text-surface-600">
          <li v-for="c in adviceChecks" :key="c.name">
            <i :class="c.passed ? 'pi pi-check' : 'pi pi-info-circle text-amber-600'" class="mr-1 text-xs" /><b>{{ c.name }}</b> — {{ c.reason }}
          </li>
        </ul>
      </template>
    </details>

    <!-- 수업 전에 먼저 볼 것: 오늘 문법과 설명 포인트 → 7단계 흐름 → 범주별 검토 -->
    <BriefingPanel :briefing="payload.briefing" />
    <LessonFrame v-if="payload.briefing?.lesson_frame" :frame="payload.briefing.lesson_frame" :drafts="payload.drafts" :culture="payload.briefing.culture" />

    <div class="space-y-4">
      <CategoryReviewCard
        v-for="c in CATEGORIES"
        :key="c"
        :category="c"
        :draft="payload.drafts[c]"
        :approved="payload.approved_categories.includes(c)"
        :decision="decisions[c] ?? { action: 'approve' }"
        @update:decision="d => (decisions[c] = d)"
      />
    </div>

    <div class="sticky bottom-0 mt-4 flex flex-wrap items-center gap-3 border-t border-surface-200 bg-surface-50/95 py-3 backdrop-blur">
      <Button
        :label="willRegenerate ? '검토 결과 보내기 (피드백한 범주는 다시 만들어요)' : '모두 확정하기'"
        icon="pi pi-send"
        :disabled="!!missingFeedback.length"
        @click="submit"
      />
      <span v-if="missingFeedback.length" class="text-sm text-red-600">피드백을 고른 범주에 내용을 적어 주세요.</span>
    </div>
  </template>

  <template v-else-if="phase === 'done' && lesson">
    <div class="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-primary-200 bg-primary-50 p-4">
      <i class="pi pi-check-circle text-xl text-primary-600" />
      <span class="font-semibold">수업안이 확정됐어요.</span>
      <div class="flex-1" />
      <RouterLink :to="`/lessons/${lesson.id}/record`"><Button label="수업 후 기록 쓰기" icon="pi pi-pencil" severity="secondary" outlined /></RouterLink>
    </div>
    <!-- 수업 전에 먼저 볼 것: 오늘 문법과 설명 포인트 → 7단계 흐름 → 범주별 검토 -->
    <BriefingPanel :briefing="lesson.briefing" />
    <LessonFrame v-if="lesson.briefing?.lesson_frame" :frame="lesson.briefing.lesson_frame" :drafts="lesson.drafts" :culture="lesson.briefing.culture" />
    <div v-if="lesson.drafts" class="space-y-4">
      <CategoryReviewCard
        v-for="c in CATEGORIES"
        :key="c"
        :category="c"
        :draft="lesson.drafts[c]"
        approved
        :decision="{ action: 'approve' }"
      />
    </div>
    <p v-else class="text-surface-500">수업안 없이 진행한 수업이에요.</p>
  </template>
</template>
