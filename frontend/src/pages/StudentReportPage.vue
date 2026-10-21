<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Skeleton from 'primevue/skeleton'
import SelectButton from 'primevue/selectbutton'
import ErrorBox from '../components/ErrorBox.vue'
import { studentsApi } from '../api/endpoints'
import { LANG_NAMES, type Lang, type ProgressReport } from '../api/types'
import { toUiError, type UiError } from '../utils'

// 학습자별 진도·향상 리포트 (기획 ADR-0019).
// 숫자와 문장 초안은 ai-server가 코드로 계산한다. 학생에게 보낼 문장은 여기서 고친 뒤 복사해 플랫폼으로 보낸다.

const props = defineProps<{ id: number }>()
const toast = useToast()

const ymd = (d: Date) => d.toLocaleDateString('sv-SE') // YYYY-MM-DD (로컬 날짜)
const daysAgo = (n: number) => ymd(new Date(Date.now() - n * 86_400_000))
const firstOfMonth = () => {
  const d = new Date()
  return ymd(new Date(d.getFullYear(), d.getMonth(), 1))
}

type Preset = '30d' | 'month' | 'all' | 'custom'
const presetOptions = [
  { label: '최근 30일', value: '30d' },
  { label: '이번 달', value: 'month' },
  { label: '전체', value: 'all' },
  { label: '직접', value: 'custom' },
]
const preset = ref<Preset>('30d')
const from = ref(daysAgo(29))
const to = ref(ymd(new Date()))

const report = ref<ProgressReport | null>(null)
const error = ref<UiError | null>(null)
const loading = ref(false)
const messages = ref<Record<string, string>>({})
const lang = ref('ko')

async function load() {
  loading.value = true
  error.value = null
  try {
    report.value = await studentsApi.report(props.id, preset.value === 'all' ? undefined : from.value, to.value)
    messages.value = { ...report.value.messages }
    if (!(lang.value in messages.value)) lang.value = 'ko'
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

function choose(p: Preset) {
  preset.value = p
  if (p === '30d') from.value = daysAgo(29)
  if (p === 'month') from.value = firstOfMonth()
  if (p !== 'custom') {
    to.value = ymd(new Date())
    load()
  }
}

const langOptions = computed(() =>
  Object.keys(messages.value).map(k => ({ label: k === 'ko' ? '한국어' : `${LANG_NAMES[k as Lang]} (학생용)`, value: k })),
)
const pct = (a: number, b: number) => (b ? Math.round((a / b) * 100) : 0)

async function copy() {
  await navigator.clipboard.writeText(messages.value[lang.value] ?? '')
  toast.add({ severity: 'success', summary: '복사했어요', detail: '플랫폼 메시지에 붙여 넣으세요', life: 2000 })
}
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <RouterLink :to="`/students/${id}`"><Button icon="pi pi-arrow-left" text severity="secondary" aria-label="학생 화면으로" /></RouterLink>
    <h1 class="m-0 text-xl font-bold">{{ report?.student.name ?? '' }} 진도 리포트</h1>
  </div>

  <section class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-surface-200 bg-white p-4">
    <SelectButton :model-value="preset" :options="presetOptions" option-label="label" option-value="value" :allow-empty="false" @update:model-value="choose" />
    <template v-if="preset === 'custom'">
      <label class="flex flex-col gap-1 text-sm"><span class="text-surface-500">시작</span><InputText v-model="from" type="date" /></label>
      <label class="flex flex-col gap-1 text-sm"><span class="text-surface-500">끝</span><InputText v-model="to" type="date" /></label>
      <Button label="보기" icon="pi pi-search" :loading="loading" @click="load" />
    </template>
  </section>

  <ErrorBox :error="error" @retry="load" />
  <div v-if="!report && !error" class="grid gap-3 md:grid-cols-3"><Skeleton v-for="i in 3" :key="i" height="8rem" /></div>

  <template v-else-if="report">
    <p class="mb-4 mt-0 text-sm text-surface-500">
      {{ report.period.from }} ~ {{ report.period.to }} · 승인된 수업 기록만 셉니다. 숫자는 코드가 계산했어요 (AI가 쓰지 않음).
    </p>

    <div class="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div class="stat"><span>수업</span><b>{{ report.lessons.count }}회</b><small>{{ report.lessons.minutes }}분 · 누적 {{ report.lessons.total_count }}회</small></div>
      <div class="stat"><span>새로 배운 문법</span><b>{{ report.new.grammar.length }}개</b><small>누적 {{ report.total.grammar }}개</small></div>
      <div class="stat"><span>새로 배운 단어</span><b>{{ report.new.vocab.length }}개</b><small>누적 {{ report.total.vocab }}개</small></div>
      <div class="stat">
        <span>지금 수준</span><b>{{ report.level_name ?? '수준 미정' }}</b>
        <small>{{ report.target_name ? `목표 ${report.target_name} · 남은 문법 ${report.remaining_to_target.count}개` : '목표 수준 없음' }}</small>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="card">
        <h2>표준 등급별로 배운 양 <small class="font-normal text-surface-500">(선생님용 — 학생 메시지에는 넣지 않아요)</small></h2>
        <div v-for="c in report.coverage" :key="c.level" class="mb-3">
          <div class="mb-1 text-sm font-semibold">{{ c.name }}</div>
          <div class="grid grid-cols-[3rem_1fr_5rem] items-center gap-2 text-sm">
            <span class="text-surface-500">문법</span><ProgressBar :value="pct(c.grammar.learned, c.grammar.total)" :show-value="false" style="height: 0.5rem" />
            <span class="text-right">{{ c.grammar.learned }}/{{ c.grammar.total }}</span>
            <span class="text-surface-500">어휘</span><ProgressBar :value="pct(c.vocab.learned, c.vocab.total)" :show-value="false" style="height: 0.5rem" />
            <span class="text-right">{{ c.vocab.learned }}/{{ c.vocab.total }}</span>
          </div>
        </div>
        <p class="mb-0 text-xs text-surface-500">교재 항목을 국립국어원 표준 교육과정 항목에 이어서 셉니다. 지금은 「한국어 1」 2~4과만 이어져 있어요.</p>
        <template v-if="report.remaining_to_target.next.length">
          <h3 class="mb-2 mt-4 text-sm font-semibold text-surface-500">목표까지 남은 문법 (앞에서 5개)</h3>
          <div class="flex flex-wrap gap-1"><Tag v-for="g in report.remaining_to_target.next" :key="g.id" :value="`${g.form} · ${g.level}급`" severity="secondary" /></div>
        </template>
      </section>

      <section class="card">
        <h2>이번 기간</h2>
        <h3>새 문법</h3>
        <div class="flex flex-wrap gap-1">
          <Tag v-for="g in report.new.grammar" :key="g.id" :value="g.form" severity="info" />
          <span v-if="!report.new.grammar.length" class="empty">없음</span>
        </div>
        <h3>새 단어</h3>
        <div class="flex flex-wrap gap-1">
          <Tag v-for="v in report.new.vocab" :key="v.word" :value="v.word" severity="secondary" />
          <span v-if="!report.new.vocab.length" class="empty">없음</span>
        </div>
        <h3>잘한 점</h3>
        <ul><li v-for="s in report.strengths" :key="s">{{ s }}</li><li v-if="!report.strengths.length" class="empty">없음</li></ul>
        <h3>해결한 약점</h3>
        <ul><li v-for="w in report.resolved_weaknesses" :key="w">{{ w }}</li><li v-if="!report.resolved_weaknesses.length" class="empty">없음</li></ul>
        <h3>반복 오류 (2번 이상)</h3>
        <ul>
          <li v-for="e in report.repeated_errors" :key="e.key">
            {{ e.student_said }} → <b>{{ e.correction }}</b> <Tag :value="`${e.count}번`" severity="warn" class="!text-xs" />
          </li>
          <li v-if="!report.repeated_errors.length" class="empty">없음</li>
        </ul>
        <h3>남은 약점</h3>
        <ul><li v-for="w in report.open_weaknesses" :key="w">{{ w }}</li><li v-if="!report.open_weaknesses.length" class="empty">없음</li></ul>
      </section>
    </div>

    <section class="card mt-4">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <h2 class="!m-0">학생에게 보낼 메시지</h2>
        <SelectButton v-model="lang" :options="langOptions" option-label="label" option-value="value" :allow-empty="false" />
        <div class="flex-1" />
        <Button label="복사" icon="pi pi-copy" @click="copy" />
      </div>
      <Message severity="info" class="mb-2 text-sm">
        개수와 늘어난 양만 넣었어요 (비율은 넣지 않음). 잘한 점·극복한 것은 수업 기록의 한국어 그대로라, 학생 언어 메시지에서는 직접 고쳐 주세요.
      </Message>
      <Textarea v-model="messages[lang]" rows="12" auto-resize class="w-full font-mono text-sm" />
    </section>
  </template>
</template>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
  background: var(--p-surface-0);
}
.stat > span {
  font-size: 0.8rem;
  color: var(--p-surface-500);
}
.stat > b {
  font-size: 1.4rem;
}
.stat > small {
  color: var(--p-surface-500);
}
.card {
  padding: 1rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
  background: var(--p-surface-0);
}
.card h2 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 700;
}
.card h3 {
  margin: 1rem 0 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--p-surface-500);
}
.card ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.9rem;
}
.empty {
  color: var(--p-surface-400);
  font-size: 0.875rem;
  list-style: none;
}
</style>
