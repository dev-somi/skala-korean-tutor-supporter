<script setup lang="ts">
// 수업 준비 탭: 학생 프로필을 다음 수업 일정 순으로 보여 주고, 카드마다 지금 할 준비 버튼 하나를 둔다 (기술 ADR-0029)
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'
import ErrorBox from '../components/ErrorBox.vue'
import PrepDialog from '../components/PrepDialog.vue'
import { lessonsApi, studentsApi } from '../api/endpoints'
import { LANG_NAMES, PERSONA_NAMES, levelName, type LessonView, type StudentSummary } from '../api/types'
import { formatDate, toUiError, type UiError } from '../utils'

const route = useRoute()
const students = ref<StudentSummary[] | null>(null)
const lessons = ref<LessonView[]>([])
const error = ref<UiError | null>(null)
const dialog = ref(false)
const dialogStudentId = ref<number | null>(null)

async function load() {
  error.value = null
  try {
    students.value = await studentsApi.list()
    // 수업 전체 목록 API가 없어서 학생별 목록을 모은다 (학생 3~10명)
    const lists = await Promise.all(students.value.map(s => lessonsApi.listByStudent(s.id)))
    lessons.value = lists.flat()
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(async () => {
  await load()
  const q = Number(route.query.student)
  if (q) openDialog(q)
})

function openDialog(studentId: number) {
  dialogStudentId.value = studentId
  dialog.value = true
}

// 학생마다 "다음 수업" = 아직 수업 전(준비 중·확정)인 수업 중 가장 이른 것
const byDate = (a: LessonView, b: LessonView) => (a.lessonDate ?? '9999').localeCompare(b.lessonDate ?? '9999') || a.id - b.id
const rows = computed(() => {
  const list = (students.value ?? []).filter(s => s.status !== 'paused').map(s => {
    const next = lessons.value.filter(l => l.studentId === s.id && (l.status === 'planned' || l.status === 'prepared')).sort(byDate)[0] ?? null
    return { student: s, next }
  })
  // 일정 있는 수업 → 날짜 미정 수업 → 다음 수업이 아직 없는 학생
  const rank = (r: (typeof list)[number]) => (r.next ? (r.next.lessonDate ? 0 : 1) : 2)
  return list.sort((a, b) => rank(a) - rank(b) || (a.next && b.next ? byDate(a.next, b.next) : a.student.name.localeCompare(b.student.name)))
})

const today = new Date().toISOString().slice(0, 10)
function dayLabel(date: string | null) {
  if (!date) return '날짜 미정'
  const diff = Math.round((new Date(date).getTime() - new Date(today).getTime()) / 86400000)
  if (diff === 0) return '오늘'
  if (diff === 1) return '내일'
  if (diff < 0) return `${-diff}일 지남`
  return `${diff}일 뒤`
}
</script>

<template>
  <div class="mb-1 flex flex-wrap items-center gap-2">
    <h1 class="m-0 text-xl font-bold">수업 준비</h1>
  </div>
  <p class="mt-0 text-sm text-surface-500">다음 수업이 가까운 학생부터 보여요. 준비하면 AI가 그 학생에게 맞춘 문법 브리핑(교재 근거)과 7단계 수업안을 만들어요.</p>
  <ErrorBox :error="error" @retry="load" />

  <div v-if="!students" class="grid gap-3"><Skeleton v-for="i in 3" :key="i" height="6rem" /></div>
  <p v-else-if="!rows.length" class="text-sm text-surface-500">먼저 <RouterLink to="/students/new">학생을 등록</RouterLink>해 주세요.</p>

  <ul v-else class="m-0 grid list-none gap-3 p-0">
    <li v-for="{ student: s, next } in rows" :key="s.id" class="flex flex-wrap items-center gap-4 rounded-xl border border-surface-200 bg-white p-4">
      <!-- 다음 수업 일정 -->
      <div class="w-24 shrink-0 text-center">
        <template v-if="next">
          <div class="text-lg font-bold" :class="next.lessonDate === today ? 'text-primary-700' : ''">{{ dayLabel(next.lessonDate) }}</div>
          <div class="text-xs text-surface-500">{{ next.lessonDate ? formatDate(next.lessonDate) : '' }}</div>
        </template>
        <div v-else class="text-sm text-surface-400">다음 수업<br />없음</div>
      </div>

      <!-- 학생 프로필 -->
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <RouterLink :to="`/students/${s.id}`" class="font-bold text-surface-900">{{ s.name }}</RouterLink>
          <Tag :value="LANG_NAMES[s.nativeLanguage]" severity="secondary" />
          <span class="text-sm font-semibold">{{ levelName(s.standardLevel) }}</span>
          <span v-if="s.persona" class="text-sm text-surface-500">· {{ PERSONA_NAMES[s.persona] }}</span>
        </div>
        <div class="mt-1 text-sm text-surface-600">
          <template v-if="next">{{ next.lessonNo }}회차 · {{ next.unitNo }}과 · {{ next.minutes }}분</template>
          <template v-else>다음 {{ s.nextUnit }}과</template>
          <span v-if="s.mainWeaknesses.length" class="text-orange-700"> · 약점 {{ s.mainWeaknesses.slice(0, 2).join(', ') }}</span>
        </div>
      </div>

      <!-- 상태와 할 일 하나 -->
      <div class="flex shrink-0 items-center gap-2">
        <template v-if="next?.status === 'prepared'">
          <Tag value="수업안 확정" severity="success" />
          <RouterLink :to="`/lessons/${next.id}/review`"><Button label="수업안 보기" icon="pi pi-eye" size="small" severity="secondary" outlined /></RouterLink>
        </template>
        <template v-else-if="next">
          <Tag value="준비 중" severity="info" />
          <RouterLink :to="`/lessons/${next.id}/review`"><Button label="이어서 준비" icon="pi pi-arrow-right" size="small" /></RouterLink>
        </template>
        <Button v-else label="수업 준비" icon="pi pi-play" size="small" @click="openDialog(s.id)" />
      </div>
    </li>
  </ul>

  <PrepDialog v-model:visible="dialog" :student-id="dialogStudentId" />
</template>
