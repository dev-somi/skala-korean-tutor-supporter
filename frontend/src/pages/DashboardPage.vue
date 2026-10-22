<script setup lang="ts">
// 대시보드: 월간 수업 달력 + 고른 날짜의 수업 준비 상태 (기획 ADR-0034)
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import ErrorBox from '../components/ErrorBox.vue'
import PrepDialog from '../components/PrepDialog.vue'
import { lessonsApi } from '../api/endpoints'
import { bookName, type LessonView } from '../api/types'
import { formatDate, toUiError, type UiError } from '../utils'

/** 로컬 날짜 → YYYY-MM-DD (toISOString은 UTC라 새벽에 하루 밀린다) */
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const today = ymd(new Date())

// 수업 하나의 상태: 날짜와 status, 준비 시작 여부로 정한다
type State = 'unprepared' | 'preparing' | 'ready' | 'toRecord' | 'recordReview' | 'recorded'
const STATES: Record<State, { label: string; dot: string; chip: string; action: string; icon: string; path: 'review' | 'record' }> = {
  unprepared: { label: '준비 전', dot: 'bg-red-500', chip: 'bg-red-50 text-red-800', action: '수업 준비', icon: 'pi pi-play', path: 'review' },
  preparing: { label: '준비 중', dot: 'bg-amber-500', chip: 'bg-amber-50 text-amber-800', action: '이어서 준비', icon: 'pi pi-arrow-right', path: 'review' },
  ready: { label: '준비 완료', dot: 'bg-emerald-500', chip: 'bg-emerald-50 text-emerald-800', action: '수업안 보기', icon: 'pi pi-eye', path: 'review' },
  toRecord: { label: '기록 필요', dot: 'bg-violet-600', chip: 'bg-violet-50 text-violet-800', action: '기록 쓰기', icon: 'pi pi-pencil', path: 'record' },
  recordReview: { label: '기록 확인 대기', dot: 'bg-violet-300', chip: 'bg-violet-50 text-violet-700', action: '기록 확인', icon: 'pi pi-check-square', path: 'record' },
  recorded: { label: '끝', dot: 'bg-surface-400', chip: 'bg-surface-100 text-surface-600', action: '기록 보기', icon: 'pi pi-file', path: 'record' },
}
function stateOf(l: LessonView): State {
  if (l.status === 'recorded') return 'recorded'
  if (l.status === 'done') return 'recordReview'
  if (l.lessonDate && l.lessonDate < today) return 'toRecord'
  if (l.status === 'prepared') return 'ready'
  return l.prepThreadId ? 'preparing' : 'unprepared'
}

// 보이는 달과 6주 격자 (일요일 시작)
const now = new Date()
const month = ref(new Date(now.getFullYear(), now.getMonth(), 1))
const selected = ref(today)
const days = computed(() => {
  const first = month.value
  const start = new Date(first.getFullYear(), first.getMonth(), 1 - first.getDay())
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    return { date: ymd(d), day: d.getDate(), inMonth: d.getMonth() === first.getMonth(), weekday: d.getDay() }
  })
})
const monthLabel = computed(() => `${month.value.getFullYear()}년 ${month.value.getMonth() + 1}월`)
function moveMonth(delta: number) {
  month.value = new Date(month.value.getFullYear(), month.value.getMonth() + delta, 1)
}
function goToday() {
  month.value = new Date(now.getFullYear(), now.getMonth(), 1)
  selected.value = today
}

const lessons = ref<LessonView[] | null>(null)
const error = ref<UiError | null>(null)
async function load() {
  error.value = null
  try {
    lessons.value = await lessonsApi.listRange(days.value[0].date, days.value[41].date)
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)
watch(month, load)

const byDate = computed(() => {
  const map: Record<string, LessonView[]> = {}
  for (const l of lessons.value ?? []) if (l.lessonDate) (map[l.lessonDate] ??= []).push(l)
  return map
})
const undated = computed(() => (lessons.value ?? []).filter(l => !l.lessonDate))
const selectedLessons = computed(() => byDate.value[selected.value] ?? [])

const dialog = ref(false)
const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']
const actionTo = (l: LessonView) => `/lessons/${l.id}/${STATES[stateOf(l)].path}`
</script>

<template>
  <ErrorBox :error="error" @retry="load" />

  <div class="mb-3 flex flex-wrap items-center gap-2">
    <h1 class="m-0 text-xl font-bold">{{ monthLabel }}</h1>
    <Button icon="pi pi-chevron-left" text rounded size="small" aria-label="이전 달" @click="moveMonth(-1)" />
    <Button label="오늘" size="small" severity="secondary" outlined @click="goToday" />
    <Button icon="pi pi-chevron-right" text rounded size="small" aria-label="다음 달" @click="moveMonth(1)" />
    <div class="flex-1" />
    <Button label="수업 잡기" icon="pi pi-plus" size="small" @click="dialog = true" />
  </div>
  <div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-surface-600">
    <span v-for="(s, key) in STATES" :key="key" class="flex items-center gap-1"><span class="h-2 w-2 rounded-full" :class="s.dot" />{{ s.label }}</span>
  </div>

  <div class="grid gap-4 lg:grid-cols-[1fr_20rem]">
    <!-- 월간 달력 -->
    <div class="overflow-hidden rounded-xl border border-surface-200 bg-white">
      <div class="grid grid-cols-7 border-b border-surface-200 text-center text-xs font-semibold text-surface-500">
        <div v-for="(w, i) in WEEKDAYS" :key="w" class="py-2" :class="{ 'text-red-500': i === 0, 'text-sky-600': i === 6 }">{{ w }}</div>
      </div>
      <div v-if="!lessons" class="p-3"><Skeleton height="24rem" /></div>
      <div v-else class="grid grid-cols-7">
        <button
          v-for="d in days"
          :key="d.date"
          type="button"
          class="cal-cell"
          :class="{ 'opacity-40': !d.inMonth, 'cal-selected': d.date === selected }"
          @click="selected = d.date"
        >
          <span class="cal-day" :class="{ 'cal-today': d.date === today, 'text-red-500': d.weekday === 0 && d.date !== today, 'text-sky-600': d.weekday === 6 && d.date !== today }">{{ d.day }}</span>
          <span v-for="l in (byDate[d.date] ?? []).slice(0, 3)" :key="l.id" class="cal-chip" :class="STATES[stateOf(l)].chip">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full" :class="STATES[stateOf(l)].dot" />
            <span class="truncate">{{ l.studentName }}</span>
          </span>
          <span v-if="(byDate[d.date]?.length ?? 0) > 3" class="text-[0.7rem] text-surface-500">+{{ byDate[d.date].length - 3 }}</span>
        </button>
      </div>
    </div>

    <!-- 고른 날짜의 수업 -->
    <aside>
      <h2 class="mb-2 mt-0 text-base font-bold">{{ formatDate(selected) }}<span v-if="selected === today" class="ml-1 text-sm text-primary-700">오늘</span></h2>
      <p v-if="lessons && !selectedLessons.length" class="text-sm text-surface-400">수업 없음</p>
      <ul class="m-0 grid list-none gap-3 p-0">
        <li v-for="l in selectedLessons" :key="l.id" class="rounded-xl border border-surface-200 bg-white p-4">
          <div class="flex items-center gap-2">
            <RouterLink :to="`/students/${l.studentId}`" class="font-bold text-surface-900">{{ l.studentName }}</RouterLink>
            <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="STATES[stateOf(l)].chip">{{ STATES[stateOf(l)].label }}</span>
          </div>
          <div class="mt-1 text-sm text-surface-600">{{ l.lessonNo }}회차 · {{ bookName(l.book) }} {{ l.unitNo }}과 · {{ l.minutes }}분</div>
          <ul class="my-3 grid list-none gap-1 p-0 text-sm">
            <li :class="l.prepThreadId || l.status !== 'planned' ? 'text-surface-800' : 'text-surface-400'">
              <i class="pi mr-1" :class="l.prepThreadId || l.status !== 'planned' ? 'pi-check-circle text-emerald-600' : 'pi-circle'" />준비 시작
            </li>
            <li :class="l.status !== 'planned' ? 'text-surface-800' : 'text-surface-400'">
              <i class="pi mr-1" :class="l.status !== 'planned' ? 'pi-check-circle text-emerald-600' : 'pi-circle'" />수업안 확정 <span class="text-xs text-surface-400">(브리핑·슬라이드·대본)</span>
            </li>
            <li v-if="l.lessonDate && l.lessonDate < today || l.status === 'done' || l.status === 'recorded'" :class="l.status === 'recorded' ? 'text-surface-800' : 'text-surface-400'">
              <i class="pi mr-1" :class="l.status === 'recorded' ? 'pi-check-circle text-emerald-600' : 'pi-circle'" />수업 기록 승인
            </li>
          </ul>
          <RouterLink :to="actionTo(l)">
            <Button
              :label="STATES[stateOf(l)].action"
              :icon="STATES[stateOf(l)].icon"
              size="small"
              :severity="stateOf(l) === 'ready' || stateOf(l) === 'recorded' ? 'secondary' : undefined"
              :outlined="stateOf(l) === 'ready' || stateOf(l) === 'recorded'"
            />
          </RouterLink>
        </li>
      </ul>

      <template v-if="undated.length">
        <h2 class="mb-2 mt-6 text-base font-bold">날짜 미정</h2>
        <ul class="m-0 grid list-none gap-2 p-0">
          <li v-for="l in undated" :key="l.id">
            <RouterLink :to="actionTo(l)" class="flex items-center gap-2 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-800 no-underline hover:border-primary-300">
              <span class="h-2 w-2 shrink-0 rounded-full" :class="STATES[stateOf(l)].dot" />
              <b>{{ l.studentName }}</b>
              <span class="truncate text-surface-500">{{ l.lessonNo }}회차 · {{ l.unitNo }}과</span>
              <span class="ml-auto shrink-0 text-xs text-surface-500">{{ STATES[stateOf(l)].label }}</span>
            </RouterLink>
          </li>
        </ul>
      </template>
    </aside>
  </div>

  <PrepDialog v-model:visible="dialog" />
</template>

<style scoped>
.cal-cell {
  display: flex;
  min-height: 6rem;
  min-width: 0;
  flex-direction: column;
  align-items: stretch;
  gap: 0.2rem;
  padding: 0.375rem;
  text-align: left;
  background: none;
  border: 0;
  border-right: 1px solid var(--p-surface-100);
  border-bottom: 1px solid var(--p-surface-100);
  cursor: pointer;
  font: inherit;
}
.cal-cell:hover {
  background: var(--p-surface-50);
}
.cal-selected {
  box-shadow: inset 0 0 0 2px var(--p-primary-400);
}
.cal-day {
  font-size: 0.8rem;
  font-weight: 600;
  width: 1.5rem;
  height: 1.5rem;
  line-height: 1.5rem;
  text-align: center;
  border-radius: 9999px;
}
.cal-today {
  background: var(--p-primary-600);
  color: white;
}
.cal-chip {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.25rem;
  border-radius: 0.375rem;
  padding: 0.05rem 0.3rem;
  font-size: 0.72rem;
  line-height: 1.2rem;
}
</style>
