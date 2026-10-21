<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Timeline from 'primevue/timeline'
import StudentForm from '../components/StudentForm.vue'
import PrepDialog from '../components/PrepDialog.vue'
import ItemChips from '../components/ItemChips.vue'
import { useItemLabels } from '../stores/itemLabels'
import ErrorBox from '../components/ErrorBox.vue'
import { lessonsApi, studentsApi } from '../api/endpoints'
import {
  LANG_NAMES, LESSON_STATUS_NAMES, PERSONA_NAMES, PERSONA_TEXTBOOKS, levelName,
  type LessonView, type StudentDetail, type StudentRequest, bookName,
} from '../api/types'
import { formatDate, toUiError, type UiError } from '../utils'

const props = defineProps<{ id: number }>()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const { label } = useItemLabels()

const student = ref<StudentDetail | null>(null)
const lessons = ref<LessonView[]>([])
const editing = ref(false)
const saving = ref(false)
const error = ref<UiError | null>(null)

async function load() {
  error.value = null
  try {
    ;[student.value, lessons.value] = await Promise.all([studentsApi.get(props.id), lessonsApi.listByStudent(props.id)])
  } catch (e) {
    error.value = toUiError(e)
  }
}
onMounted(load)

const active = computed(() => student.value?.weaknesses.filter(w => !w.resolved) ?? [])
const resolved = computed(() => student.value?.weaknesses.filter(w => w.resolved) ?? [])
const materials = computed(() => lessons.value.filter(l => l.status !== 'planned' && l.briefing))

async function save(body: StudentRequest) {
  saving.value = true
  try {
    student.value = await studentsApi.update(props.id, body)
    editing.value = false
    toast.add({ severity: 'success', summary: '저장했어요', life: 2000 })
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    saving.value = false
  }
}

function remove() {
  confirm.require({
    message: `${student.value?.name} 학생과 수업 기록을 모두 지울까요? 되돌릴 수 없어요.`,
    header: '학생 삭제',
    acceptProps: { label: '삭제', severity: 'danger' },
    rejectProps: { label: '취소', severity: 'secondary', text: true },
    accept: async () => {
      await studentsApi.remove(props.id)
      router.push('/students')
    },
  })
}

// --- 다음 수업 준비: 공용 다이얼로그 (수업 준비 탭과 같은 폼) ---
const prepDialog = ref(false)

const statusSeverity: Record<string, string> = { planned: 'secondary', prepared: 'info', done: 'warn', recorded: 'success' }
</script>

<template>
  <ErrorBox :error="error" @retry="load" />
  <template v-if="student">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <h1 class="m-0 text-xl font-bold">{{ student.name }}</h1>
      <Tag :value="LANG_NAMES[student.nativeLanguage]" severity="secondary" />
      <Tag v-if="student.status === 'paused'" value="쉬는 중" severity="contrast" />
      <div class="flex-1" />
      <Button label="다음 수업 준비" icon="pi pi-play" @click="prepDialog = true" />
      <RouterLink :to="`/students/${student.id}/report`"><Button label="진도 리포트" icon="pi pi-chart-line" severity="secondary" outlined /></RouterLink>
      <Button :label="editing ? '편집 닫기' : '정보 수정'" icon="pi pi-pencil" severity="secondary" outlined @click="editing = !editing" />
      <Button icon="pi pi-trash" severity="danger" text aria-label="학생 삭제" @click="remove" />
    </div>

    <section v-if="editing" class="mb-6 rounded-xl border border-surface-200 bg-white p-4">
      <StudentForm :model-value="student" :saving="saving" @submit="save" @cancel="editing = false" />
    </section>

    <div v-else class="mb-6 grid gap-4 lg:grid-cols-3">
      <section class="rounded-xl border border-surface-200 bg-white p-4 lg:col-span-2">
        <h2 class="mb-3 mt-0 text-base font-bold">프로필</h2>
        <dl class="m-0 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-2 text-sm">
          <dt class="text-surface-500">수준</dt>
          <dd class="m-0">
            <span :class="student.standardLevel == null ? 'font-semibold text-orange-600' : 'font-semibold'">{{ levelName(student.standardLevel) }}</span>
            <span v-if="student.levelAssessedOn" class="text-surface-500"> · 레벨테스트 {{ student.levelAssessedOn }}</span>
            <span v-if="student.targetLevel" class="text-surface-500"> · 목표 {{ levelName(student.targetLevel) }}</span>
            <div v-if="student.level" class="text-surface-600">{{ student.level }}</div>
            <div v-if="student.standardLevel == null" class="text-xs text-orange-600">[정보 수정]에서 레벨테스트 결과로 골라 주세요</div>
          </dd>
          <dt class="text-surface-500">학습 목적</dt>
          <dd class="m-0">{{ student.persona ? `${PERSONA_NAMES[student.persona]} (중심 교재: ${PERSONA_TEXTBOOKS[student.persona]})` : '-' }}</dd>
          <dt class="text-surface-500">목표</dt><dd class="m-0">{{ student.goals.join(' · ') || '-' }}</dd>
          <dt class="text-surface-500">관심사</dt><dd class="m-0">{{ student.interests.join(' · ') || '-' }}</dd>
          <dt class="text-surface-500">다음 과</dt><dd class="m-0">{{ bookName(student.nextBook) }} {{ student.nextUnit }}과 · 기본 {{ student.lessonMinutesDefault }}분</dd>
          <dt class="text-surface-500">메모</dt><dd class="m-0 pre-line">{{ student.notes || '-' }}</dd>
        </dl>
      </section>
      <section class="rounded-xl border border-surface-200 bg-white p-4">
        <h2 class="mb-3 mt-0 text-base font-bold">약점</h2>
        <ul class="m-0 list-none space-y-2 p-0 text-sm">
          <li v-for="w in active" :key="w.id!" class="flex items-start gap-2">
            <i class="pi pi-circle-fill mt-1 text-[0.5rem] text-orange-500" />
            <span class="flex-1">{{ w.description }} <span v-if="w.itemId" class="text-xs text-surface-500" :title="w.itemId">· {{ label(w.itemId) }}</span></span>
            <span class="text-xs text-surface-400">{{ formatDate(w.createdAt) }}~</span>
          </li>
          <li v-if="!active.length" class="text-surface-400">남은 약점 없음</li>
        </ul>
        <template v-if="resolved.length">
          <h3 class="mb-2 mt-4 text-sm font-semibold text-surface-500">해결됨</h3>
          <ul class="m-0 list-none space-y-1 p-0 text-sm text-surface-500">
            <li v-for="w in resolved" :key="w.id!" class="flex gap-2">
              <i class="pi pi-check mt-0.5 text-xs text-primary-600" />
              <span class="flex-1 line-through">{{ w.description }}</span>
              <span class="text-xs">{{ formatDate(w.createdAt) }} → {{ formatDate(w.resolvedAt) }}</span>
            </li>
          </ul>
        </template>
      </section>
    </div>

    <div class="grid gap-4 lg:grid-cols-3">
      <section class="rounded-xl border border-surface-200 bg-white p-4 lg:col-span-2">
        <h2 class="mb-3 mt-0 text-base font-bold">수업 이력</h2>
        <p v-if="!lessons.length" class="text-sm text-surface-400">아직 수업이 없어요. [다음 수업 준비]로 시작하세요.</p>
        <Timeline v-else :value="lessons" class="[&_.p-timeline-event-opposite]:!hidden">
          <template #marker="{ item }">
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary-50 text-xs font-bold text-primary-700">{{ item.lessonNo }}</span>
          </template>
          <template #content="{ item }">
            <div class="mb-4">
              <div class="flex flex-wrap items-center gap-2">
                <b>{{ item.lessonNo }}회차</b>
                <span class="text-sm text-surface-500">{{ formatDate(item.lessonDate) }} · {{ bookName(item.book) }} {{ item.unitNo }}과 · {{ item.minutes }}분</span>
                <Tag :value="LESSON_STATUS_NAMES[item.status]" :severity="statusSeverity[item.status]" />
              </div>
              <div v-if="item.coveredItemIds.length" class="mt-1"><ItemChips :ids="item.coveredItemIds" /></div>
              <div class="mt-2 flex flex-wrap gap-2">
                <RouterLink v-if="item.status === 'planned' || item.plan" :to="`/lessons/${item.id}/review`">
                  <Button :label="item.status === 'planned' ? '수업 준비 / 검토' : '수업안 보기'" size="small" severity="secondary" outlined />
                </RouterLink>
                <RouterLink :to="`/lessons/${item.id}/record`">
                  <Button :label="item.status === 'recorded' ? '수업 기록 보기' : '수업 후 기록 (메모·녹취록)'" size="small" severity="secondary" outlined />
                </RouterLink>
              </div>
            </div>
          </template>
        </Timeline>
      </section>
      <section class="rounded-xl border border-surface-200 bg-white p-4">
        <h2 class="mb-3 mt-0 text-base font-bold">확정한 수업안</h2>
        <p v-if="!materials.length" class="text-sm text-surface-400">아직 없음</p>
        <ul class="m-0 list-none space-y-2 p-0 text-sm">
          <li v-for="l in materials" :key="l.id" class="flex flex-wrap items-center gap-2">
            <span class="flex-1">{{ l.lessonNo }}회차 · {{ bookName(l.book) }} {{ l.unitNo }}과</span>
            <RouterLink :to="`/lessons/${l.id}/review`"><Button label="수업안 보기" icon="pi pi-eye" size="small" text /></RouterLink>
          </li>
        </ul>
      </section>
    </div>

    <PrepDialog v-model:visible="prepDialog" :student-id="student.id" />
  </template>
</template>
