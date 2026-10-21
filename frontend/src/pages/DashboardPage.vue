<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'
import ErrorBox from '../components/ErrorBox.vue'
import StudentCard from '../components/StudentCard.vue'
import { dashboardApi, studentsApi } from '../api/endpoints'
import { levelName, type StudentSummary, type TimeMetrics, type Todos } from '../api/types'
import { formatDate, formatDateTime, toUiError, type UiError } from '../utils'

const students = ref<StudentSummary[] | null>(null)
const todos = ref<Todos | null>(null)
const metrics = ref<TimeMetrics | null>(null)
const error = ref<UiError | null>(null)

async function load() {
  error.value = null
  try {
    ;[students.value, todos.value, metrics.value] = await Promise.all([studentsApi.list(), dashboardApi.todos(), dashboardApi.metrics()])
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

const todoCount = () => (todos.value ? todos.value.pendingRecords.length + todos.value.pendingPrep.length + todos.value.toRecord.length + todos.value.pendingLevelTests.length : 0)
</script>

<template>
  <ErrorBox :error="error" @retry="load" />

  <section class="mb-8">
    <h2 class="mb-3 mt-0 flex items-center gap-2 text-lg font-bold">
      할 일 <Tag v-if="todos" :value="String(todoCount())" :severity="todoCount() ? 'warn' : 'success'" rounded />
    </h2>
    <div v-if="!todos" class="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><Skeleton v-for="i in 4" :key="i" height="6rem" /></div>
    <div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <Card class="!shadow-sm">
        <template #title><span class="text-base"><i class="pi pi-inbox mr-1 text-orange-500" />미처리 수업 기록</span></template>
        <template #content>
          <p v-if="!todos.pendingRecords.length" class="m-0 text-sm text-surface-400">없음</p>
          <RouterLink v-for="r in todos.pendingRecords" :key="r.lessonId" :to="`/lessons/${r.lessonId}/record`" class="todo-link">
            <b>{{ r.studentName }}</b> {{ r.lessonNo }}회차 <span class="text-surface-400">· {{ formatDateTime(r.updatedAt) }}</span>
          </RouterLink>
        </template>
      </Card>
      <Card class="!shadow-sm">
        <template #title><span class="text-base"><i class="pi pi-file-edit mr-1 text-sky-500" />승인 대기 수업안</span></template>
        <template #content>
          <p v-if="!todos.pendingPrep.length" class="m-0 text-sm text-surface-400">없음</p>
          <RouterLink v-for="l in todos.pendingPrep" :key="l.id" :to="`/lessons/${l.id}/review`" class="todo-link">
            <b>{{ l.studentName }}</b> {{ l.lessonNo }}회차 · {{ l.unitNo }}과 {{ l.minutes }}분
          </RouterLink>
        </template>
      </Card>
      <Card class="!shadow-sm">
        <template #title><span class="text-base"><i class="pi pi-pencil mr-1 text-violet-500" />기록을 쓸 수업</span></template>
        <template #content>
          <p v-if="!todos.toRecord.length" class="m-0 text-sm text-surface-400">없음</p>
          <RouterLink v-for="l in todos.toRecord" :key="l.id" :to="`/lessons/${l.id}/record`" class="todo-link">
            <b>{{ l.studentName }}</b> {{ l.lessonNo }}회차 <span class="text-surface-400">· {{ formatDate(l.lessonDate) }}</span>
          </RouterLink>
        </template>
      </Card>
      <Card class="!shadow-sm">
        <template #title><span class="text-base"><i class="pi pi-chart-bar mr-1 text-emerald-500" />확인할 레벨테스트</span></template>
        <template #content>
          <p v-if="!todos.pendingLevelTests.length" class="m-0 text-sm text-surface-400">없음</p>
          <RouterLink v-for="t in todos.pendingLevelTests" :key="t.id" :to="`/level-test/results/${t.id}`" class="todo-link">
            <b>{{ levelName(t.suggestedLevel) }}</b> 추천 <span class="text-surface-400">· {{ formatDateTime(t.takenAt) }}</span>
          </RouterLink>
        </template>
      </Card>
    </div>
  </section>

  <section class="mb-8">
    <div class="mb-3 flex items-center gap-2">
      <h2 class="m-0 text-lg font-bold">학생</h2>
      <RouterLink to="/students" class="text-sm">전체 보기 →</RouterLink>
      <div class="flex-1" />
      <RouterLink to="/students/new"><Button label="학생 등록" icon="pi pi-user-plus" size="small" /></RouterLink>
    </div>
    <div v-if="!students" class="grid gap-3 md:grid-cols-3"><Skeleton v-for="i in 3" :key="i" height="8rem" /></div>
    <p v-else-if="!students.length" class="text-surface-500">아직 학생이 없어요. [학생 등록]을 누르거나 채팅에 학생 설명을 써 보세요.</p>
    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <StudentCard v-for="s in students" :key="s.id" :student="s" />
    </div>
  </section>

  <section v-if="metrics">
    <div class="mb-3 flex items-center gap-2">
      <h2 class="m-0 text-lg font-bold">시간 측정</h2>
      <RouterLink to="/metrics" class="text-sm">자세히 →</RouterLink>
    </div>
    <div class="grid gap-3 md:grid-cols-2">
      <div v-for="(m, kind) in metrics" :key="kind" class="rounded-xl border border-surface-200 bg-white p-4">
        <div class="text-sm text-surface-500">{{ kind === 'prep' ? '수업 준비' : '수업 후 정리' }} · {{ m.sessions }}회</div>
        <div class="text-2xl font-bold">{{ m.avgTotalMinutes ?? '-' }}<span class="text-base font-normal">분</span></div>
        <div class="text-sm text-surface-500">
          기준 {{ m.baselineMinutes ?? '미입력' }}{{ m.baselineMinutes ? '분' : '' }}
          <span v-if="m.reductionPercent !== null" :class="m.reductionPercent >= 0 ? 'text-primary-700' : 'text-red-600'" class="font-semibold">
            · {{ m.reductionPercent >= 0 ? m.reductionPercent + '% 감소' : -m.reductionPercent + '% 증가' }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.todo-link {
  display: block;
  padding: 0.375rem 0;
  font-size: 0.9rem;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid var(--p-surface-100);
}
.todo-link:hover {
  color: var(--p-primary-700);
}
</style>
