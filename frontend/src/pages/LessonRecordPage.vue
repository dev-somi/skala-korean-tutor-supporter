<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Textarea from 'primevue/textarea'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ProgressSteps from '../components/ProgressSteps.vue'
import ErrorBox from '../components/ErrorBox.vue'
import { ApiError } from '../api/http'
import { lessonsApi, recordsApi, studentsApi } from '../api/endpoints'
import {
  CATEGORIES, CATEGORY_NAMES, LANG_NAMES, type FeedbackMessage, type LessonView, type ProgressEvent, type RecordView, type StudentDetail,
} from '../api/types'
import { useHandoffStore } from '../stores/handoff'
import { formatDateTime, toUiError, type UiError } from '../utils'

const props = defineProps<{ id: number }>()
const router = useRouter()
const toast = useToast()
const handoff = useHandoffStore()

type Phase = 'loading' | 'input' | 'running' | 'review' | 'approved'
const phase = ref<Phase>('loading')
const lesson = ref<LessonView | null>(null)
const student = ref<StudentDetail | null>(null)
const record = ref<RecordView | null>(null)
const note = ref('')
const noteStartedAt = ref<string | null>(null)
const steps = ref<ProgressEvent[]>([])
const error = ref<UiError | null>(null)
let abort: AbortController | null = null
let lastAction: () => void = () => {}
onBeforeUnmount(() => abort?.abort())

// --- 항목별 승인 상태 (체크를 풀면 반영하지 않는다, PRD F4-4) ---
const covered = ref<string[]>([])
const strengths = ref<boolean[]>([])
const errorsOn = ref<boolean[]>([])
const changesOn = ref<boolean[]>([])
const homeworkOn = ref<boolean[]>([])
const nextNote = ref('')
const message = ref<FeedbackMessage>({ target_lang_text: '', korean_text: '' })
const nextUnit = ref<number | null>(null)
const approving = ref(false)

// 녹취록(.txt)을 불러와 메모 칸에 넣는다. 이후 흐름은 메모와 같다 (기획 ADR-0025)
const NOTE_MAX = 8000 // backend RecordRequest·ai-server raw_note 상한과 같다
const fileInput = ref<HTMLInputElement | null>(null)
async function loadTranscript(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 같은 파일을 다시 고를 수 있게
  if (!file) return
  const text = (await file.text()).trim()
  note.value = note.value.trim() ? `${note.value.trim()}\n\n[녹취록: ${file.name}]\n${text}` : text
  onNoteInput()
  toast.add({ severity: 'info', summary: `${file.name}을 불러왔어요 (${text.length.toLocaleString()}자)`, life: 2500 })
}
const tooLong = computed(() => note.value.length > NOTE_MAX)

function onNoteInput() {
  // 메모를 쓰기 시작한 시각 = 수업 후 정리 시작 (F7-2)
  if (!noteStartedAt.value) noteStartedAt.value = new Date().toISOString()
}

async function init() {
  error.value = null
  try {
    lesson.value = await lessonsApi.get(props.id)
    student.value = await studentsApi.get(lesson.value.studentId)
    try {
      record.value = await recordsApi.get(props.id)
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e
      record.value = null
    }
    if (record.value?.approvedAt) phase.value = 'approved'
    else if (record.value) showReview(record.value)
    else {
      const fromChat = handoff.takeNote(props.id)
      if (fromChat) {
        note.value = fromChat
        onNoteInput()
      }
      phase.value = 'input'
    }
  } catch (e) {
    error.value = toUiError(e)
    lastAction = init
  }
}
onMounted(init)

function showReview(r: RecordView) {
  record.value = r
  note.value = r.rawNote
  const d = r.draft
  covered.value = [...d.covered_item_ids]
  strengths.value = d.strengths.map(() => true)
  errorsOn.value = d.errors.map(() => true)
  changesOn.value = d.weakness_changes.map(() => true)
  homeworkOn.value = d.homework.map(() => true)
  nextNote.value = d.next_lesson_note
  message.value = { ...d.feedback_message }
  nextUnit.value = student.value?.nextUnit ?? null
  phase.value = 'review'
}

async function makeDraft() {
  abort?.abort()
  abort = new AbortController()
  error.value = null
  steps.value = []
  phase.value = 'running'
  lastAction = makeDraft
  let done = false
  try {
    await recordsApi.draft(props.id, note.value, noteStartedAt.value, (event, data) => {
      if (event === 'node_finished') steps.value.push(data)
      else if (event === 'done') done = true
      else if (event === 'error') error.value = { message: data.message, retryable: data.retryable }
    }, abort.signal)
    if (done) showReview(await recordsApi.get(props.id))
  } catch (e) {
    if ((e as Error).name !== 'AbortError') error.value = toUiError(e)
  }
  if (phase.value === 'running') phase.value = record.value ? 'review' : 'input'
}

const weaknessName = (id: number | null) => student.value?.weaknesses.find(w => w.id === id)?.description

async function approve() {
  const d = record.value!.draft
  approving.value = true
  error.value = null
  lastAction = approve
  try {
    await recordsApi.approve(props.id, {
      coveredItemIds: covered.value,
      strengths: d.strengths.filter((_, i) => strengths.value[i]),
      errors: d.errors.filter((_, i) => errorsOn.value[i]),
      weaknessChanges: d.weakness_changes
        .filter((_, i) => changesOn.value[i])
        .map(c => ({ action: c.action, weaknessId: c.weakness_id, itemId: c.item_id, description: c.description })),
      homework: d.homework.filter((_, i) => homeworkOn.value[i]),
      nextLessonNote: nextNote.value,
      feedbackMessage: message.value,
      nextUnit: nextUnit.value,
    })
    toast.add({ severity: 'success', summary: '학생 프로필과 수업 이력에 반영했어요', life: 3000 })
    router.push(`/students/${lesson.value!.studentId}`)
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    approving.value = false
  }
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text)
  toast.add({ severity: 'info', summary: '복사했어요', life: 1500 })
}

const approved = computed(() => record.value?.approved as
  | { strengths?: string[]; errors?: { student_said: string; correction: string }[]; weaknessChanges?: { action: string; description: string }[];
      homework?: { description: string }[]; nextLessonNote?: string; feedbackMessage?: FeedbackMessage; coveredItemIds?: string[] }
  | null)
const planIds = computed(() => (lesson.value?.plan ? CATEGORIES.flatMap(c => lesson.value!.plan![c]?.item_ids ?? []) : []))
</script>

<template>
  <div v-if="lesson" class="mb-4">
    <RouterLink :to="`/students/${lesson.studentId}`" class="text-sm">← {{ lesson.studentName }}</RouterLink>
    <h1 class="m-0 text-xl font-bold">{{ lesson.lessonNo }}회차 수업 후 기록 <span class="text-base font-normal text-surface-500">· {{ lesson.unitNo }}과</span></h1>
  </div>
  <ErrorBox :error="error" @retry="lastAction()" />

  <!-- 1) 메모 입력 -->
  <section v-if="phase === 'input' || phase === 'running'" class="grid gap-4 lg:grid-cols-[1fr_18rem]">
    <div class="rounded-xl border border-surface-200 bg-white p-4">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <h2 class="m-0 text-base font-bold">수업 메모 · 녹취록</h2>
        <div class="flex-1" />
        <input ref="fileInput" type="file" accept=".txt,text/plain" class="hidden" @change="loadTranscript" />
        <Button label="녹취록 파일 불러오기 (.txt)" icon="pi pi-upload" size="small" severity="secondary" outlined :disabled="phase === 'running'" @click="fileInput?.click()" />
      </div>
      <p class="mt-0 text-sm text-surface-500">짧게 써도 되고, 수업 녹음을 텍스트로 바꾼 파일을 불러와도 돼요. AI가 다룬 항목, 잘한 점·틀린 점, 약점 변화, 숙제, 학생에게 보낼 메시지를 정리해요. 반영은 확인 후에만 해요.</p>
      <Textarea v-model="note" rows="6" auto-resize class="max-h-[28rem] w-full !overflow-y-auto" :disabled="phase === 'running'" placeholder="3과 1~10 단어 함. '-습니다' 잘함. '을/를' 받침 구분 계속 틀림. 숙제는 연습문제 2번" @input="onNoteInput" />
      <div class="mt-2 flex flex-wrap items-center gap-3">
        <Button label="AI로 정리하기" icon="pi pi-sparkles" :loading="phase === 'running'" :disabled="!note.trim() || tooLong" @click="makeDraft" />
        <span class="text-xs" :class="tooLong ? 'font-semibold text-red-600' : 'text-surface-400'">{{ note.length.toLocaleString() }} / {{ NOTE_MAX.toLocaleString() }}자</span>
        <span v-if="tooLong" class="text-xs text-red-600">너무 길어요. 수업 핵심 부분만 남겨 주세요.</span>
      </div>
      <ProgressSteps v-if="phase === 'running'" :steps="steps" running title="정리하는 중" class="mt-4" />
    </div>
    <aside v-if="lesson?.plan" class="rounded-xl border border-surface-200 bg-white p-4 text-sm">
      <h3 class="mb-2 mt-0 text-sm font-bold">수업 준비 때 계획</h3>
      <div v-for="c in CATEGORIES" :key="c" class="mb-2">
        <div class="font-semibold text-surface-600">{{ CATEGORY_NAMES[c] }} · {{ lesson.plan[c]?.minutes }}분</div>
        <code v-for="id in lesson.plan[c]?.item_ids" :key="id" class="mr-1 text-xs">{{ id }}</code>
      </div>
    </aside>
  </section>

  <!-- 2) AI 초안 항목별 검토 -->
  <section v-else-if="phase === 'review' && record" class="space-y-4">
    <Message v-for="(w, i) in record.draft.warnings" :key="i" severity="warn">{{ w }}</Message>

    <div class="rounded-xl border border-surface-200 bg-white p-4">
      <div class="mb-2 flex items-center gap-2">
        <h2 class="m-0 text-base font-bold">수업 메모</h2>
        <Button label="메모 고쳐서 다시 정리" icon="pi pi-refresh" size="small" text @click="phase = 'input'" />
      </div>
      <p class="m-0 max-h-60 overflow-y-auto pre-line text-sm text-surface-600">{{ record.rawNote }}</p>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-xl border border-surface-200 bg-white p-4">
        <h3 class="mb-2 mt-0 text-sm font-bold">다룬 교재 항목 → 수업 이력</h3>
        <div class="flex flex-wrap gap-2">
          <label v-for="id in record.draft.covered_item_ids" :key="id" class="flex items-center gap-1 rounded bg-surface-50 px-2 py-1 text-sm">
            <Checkbox v-model="covered" :value="id" /> <code>{{ id }}</code>
            <Tag v-if="planIds.length && !planIds.includes(id)" value="계획 밖" severity="secondary" class="!text-[0.65rem]" />
          </label>
        </div>
        <h3 class="mb-2 mt-4 text-sm font-bold">잘한 점</h3>
        <label v-for="(s, i) in record.draft.strengths" :key="i" class="check-row"><Checkbox v-model="strengths[i]" binary /> {{ s }}</label>
        <h3 class="mb-2 mt-4 text-sm font-bold">틀린 점</h3>
        <label v-for="(e, i) in record.draft.errors" :key="i" class="check-row">
          <Checkbox v-model="errorsOn[i]" binary />
          <span><s class="text-red-600">{{ e.student_said }}</s> → <b>{{ e.correction }}</b> <code v-if="e.item_id" class="text-xs text-surface-500">{{ e.item_id }}</code>
            <span v-if="e.note" class="block text-xs text-surface-500">{{ e.note }}</span></span>
        </label>
        <p v-if="!record.draft.errors.length" class="m-0 text-sm text-surface-400">없음</p>
      </div>

      <div class="rounded-xl border border-surface-200 bg-white p-4">
        <h3 class="mb-2 mt-0 text-sm font-bold">약점 변경 → 학생 프로필</h3>
        <label v-for="(c, i) in record.draft.weakness_changes" :key="i" class="check-row">
          <Checkbox v-model="changesOn[i]" binary />
          <Tag :value="c.action === 'add' ? '추가' : '해결'" :severity="c.action === 'add' ? 'warn' : 'success'" />
          <span>{{ c.action === 'resolve' ? weaknessName(c.weakness_id) ?? c.description : c.description }} <code v-if="c.item_id" class="text-xs text-surface-500">{{ c.item_id }}</code></span>
        </label>
        <p v-if="!record.draft.weakness_changes.length" class="m-0 text-sm text-surface-400">변경 없음</p>
        <h3 class="mb-2 mt-4 text-sm font-bold">숙제</h3>
        <label v-for="(h, i) in record.draft.homework" :key="i" class="check-row">
          <Checkbox v-model="homeworkOn[i]" binary /> {{ h.description }} <code v-if="h.item_id" class="text-xs text-surface-500">{{ h.item_id }}</code>
        </label>
        <p v-if="!record.draft.homework.length" class="m-0 text-sm text-surface-400">없음</p>
        <h3 class="mb-2 mt-4 text-sm font-bold">다음 수업 메모</h3>
        <Textarea v-model="nextNote" rows="2" auto-resize class="w-full" />
        <label class="mt-3 flex items-center gap-2 text-sm font-bold">다음에 배울 과 <InputNumber v-model="nextUnit" :min="1" :input-style="{ width: '4.5rem' }" suffix="과" /></label>
      </div>
    </div>

    <div class="rounded-xl border border-surface-200 bg-white p-4">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <h3 class="m-0 text-sm font-bold">학생에게 보낼 메시지 ({{ LANG_NAMES[lesson!.targetLang] }})</h3>
        <Tag v-if="record.draft.validation" :value="record.draft.validation.is_acceptable ? '검토 통과' : '검토 미통과'" :severity="record.draft.validation.is_acceptable ? 'success' : 'warn'"
             v-tooltip.top="record.draft.validation.reasoning" />
        <div class="flex-1" />
        <Button label="복사" icon="pi pi-copy" size="small" severity="secondary" outlined @click="copy(message.target_lang_text)" />
      </div>
      <div class="grid gap-3 lg:grid-cols-2">
        <Textarea v-model="message.target_lang_text" rows="7" auto-resize class="w-full" />
        <Textarea v-model="message.korean_text" rows="7" auto-resize class="w-full bg-surface-50" />
      </div>
      <p v-if="record.draft.validation && !record.draft.validation.is_acceptable" class="mb-0 mt-2 text-sm text-orange-700">검토 의견: {{ record.draft.validation.reasoning }}</p>
    </div>

    <div class="sticky bottom-0 flex items-center gap-3 border-t border-surface-200 bg-surface-50/95 py-3 backdrop-blur">
      <Button label="체크한 항목 승인하고 반영" icon="pi pi-check" :loading="approving" @click="approve" />
      <span class="text-sm text-surface-500">체크를 푼 항목은 반영하지 않아요.</span>
    </div>
  </section>

  <!-- 3) 승인 완료 -->
  <section v-else-if="phase === 'approved' && record && approved" class="space-y-4">
    <Message severity="success">{{ formatDateTime(record.approvedAt) }}에 승인해서 반영했어요.</Message>
    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-xl border border-surface-200 bg-white p-4 text-sm">
        <h3 class="mb-2 mt-0 font-bold">다룬 항목</h3>
        <code v-for="id in approved.coveredItemIds" :key="id" class="mr-1 text-xs">{{ id }}</code>
        <h3 class="mb-2 mt-4 font-bold">잘한 점</h3>
        <ul class="m-0 pl-5"><li v-for="s in approved.strengths" :key="s">{{ s }}</li></ul>
        <h3 class="mb-2 mt-4 font-bold">틀린 점</h3>
        <ul class="m-0 pl-5"><li v-for="(e, i) in approved.errors" :key="i">{{ e.student_said }} → {{ e.correction }}</li></ul>
        <h3 class="mb-2 mt-4 font-bold">약점 변경</h3>
        <ul class="m-0 pl-5"><li v-for="(c, i) in approved.weaknessChanges" :key="i">{{ c.action === 'add' ? '추가' : '해결' }}: {{ c.description }}</li></ul>
        <h3 class="mb-2 mt-4 font-bold">숙제</h3>
        <ul class="m-0 pl-5"><li v-for="(h, i) in approved.homework" :key="i">{{ h.description }}</li></ul>
        <h3 class="mb-2 mt-4 font-bold">다음 수업</h3>
        <p class="m-0">{{ approved.nextLessonNote || '-' }}</p>
      </div>
      <div v-if="approved.feedbackMessage" class="rounded-xl border border-surface-200 bg-white p-4 text-sm">
        <div class="mb-2 flex items-center"><h3 class="m-0 flex-1 font-bold">보낸 메시지</h3>
          <Button label="복사" icon="pi pi-copy" size="small" severity="secondary" outlined @click="copy(approved.feedbackMessage!.target_lang_text)" /></div>
        <p class="pre-line">{{ approved.feedbackMessage.target_lang_text }}</p>
        <p class="pre-line text-surface-500">{{ approved.feedbackMessage.korean_text }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.check-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.3rem 0;
  font-size: 0.9rem;
}
</style>
