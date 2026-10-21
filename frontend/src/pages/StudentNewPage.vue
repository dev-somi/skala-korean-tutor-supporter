<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'
import StudentForm from '../components/StudentForm.vue'
import ErrorBox from '../components/ErrorBox.vue'
import { levelTestApi, studentsApi } from '../api/endpoints'
import type { IntakeResult, StudentRequest } from '../api/types'
import { useHandoffStore } from '../stores/handoff'
import { toUiError, type UiError } from '../utils'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const handoff = useHandoffStore()

const empty = (): StudentRequest => ({
  name: '', nativeLanguage: 'ja', level: '', standardLevel: null, targetLevel: null, levelAssessedOn: null, persona: null,
  goals: [], interests: [], nextUnit: 1,
  lessonMinutesDefault: 50, notes: '', status: 'active', weaknesses: [],
})

const form = ref<StudentRequest>(empty())
const text = ref('')
const warnings = ref<string[]>([])
const fromAi = ref(false)
const drafting = ref(false)
const saving = ref(false)
const error = ref<UiError | null>(null)

/** AI 초안 → 폼 값. 비어 있는 칸은 기본값을 쓴다. 저장은 선생님이 누를 때만 (PRD F1-2 HITL) */
function applyIntake(result: IntakeResult) {
  const d = result.draft
  form.value = {
    ...empty(),
    name: d.name ?? '',
    nativeLanguage: d.native_language ?? 'ja',
    level: d.level ?? form.value.level,
    // 레벨테스트에서 넘어온 값이 있으면 그걸 지킨다. AI는 메모에 등급이 분명할 때만 채운다
    standardLevel: form.value.standardLevel ?? d.standard_level,
    levelAssessedOn: form.value.levelAssessedOn,
    targetLevel: d.target_level,
    persona: d.persona,
    goals: d.goals,
    interests: d.interests,
    nextUnit: d.next_unit ?? 1,
    lessonMinutesDefault: d.lesson_minutes_default ?? 50,
    notes: d.notes,
    weaknesses: d.weaknesses.map(w => ({ id: null, itemId: w.item_id, description: w.description, resolved: false })),
  }
  warnings.value = result.warnings
  fromAi.value = true
}

// 레벨테스트 결과 카드에서 [새 학생으로 등록]을 누르고 왔을 때 (?result=7&level=2&assessedOn=2026-10-20&note=…)
// 저장하면 그 결과를 새 학생에 반영해서 확인 대기에서 뺀다 (기획 ADR-0021)
const q = route.query
const resultId = /^\d+$/.test(String(q.result ?? '')) ? Number(q.result) : null
if (q.level != null && /^[0-6]$/.test(String(q.level))) {
  form.value = {
    ...form.value,
    standardLevel: Number(q.level),
    levelAssessedOn: typeof q.assessedOn === 'string' ? q.assessedOn : null,
    level: typeof q.note === 'string' ? q.note : '',
  }
}
const fromLevelTest = form.value.standardLevel != null

const fromChat = handoff.takeIntake()
if (fromChat) applyIntake(fromChat)

async function draft() {
  drafting.value = true
  error.value = null
  try {
    applyIntake(await studentsApi.intake(text.value))
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    drafting.value = false
  }
}

async function save(body: StudentRequest) {
  saving.value = true
  error.value = null
  try {
    const created = await studentsApi.create(body)
    if (resultId != null && body.standardLevel != null) await levelTestApi.apply(resultId, created.id, body.standardLevel)
    toast.add({ severity: 'success', summary: '저장했어요', detail: created.name, life: 2500 })
    router.push(`/students/${created.id}`)
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <h1 class="mb-4 mt-0 text-xl font-bold">학생 등록</h1>
  <div class="grid gap-6 lg:grid-cols-[22rem_1fr]">
    <section class="rounded-xl border border-surface-200 bg-white p-4">
      <h2 class="mb-2 mt-0 text-base font-bold"><i class="pi pi-sparkles mr-1 text-primary-600" />자연어로 채우기</h2>
      <p class="mt-0 text-sm text-surface-500">체험수업 메모를 그대로 붙여 넣으면 AI가 카드 칸을 채운 초안을 만들어요. 저장은 확인 후에 직접 누르세요.</p>
      <Textarea v-model="text" rows="7" auto-resize class="w-full" placeholder="일본인 대학생 유이, 한글은 읽음, 드라마 좋아하고 내년에 서울 여행 가고 싶대. 받침 발음이 약함" />
      <Button label="초안 만들기" icon="pi pi-bolt" class="mt-2" :loading="drafting" :disabled="!text.trim()" @click="draft" />
    </section>
    <section class="rounded-xl border border-surface-200 bg-white p-4">
      <Message v-if="fromLevelTest" severity="success" class="mb-3">레벨테스트 결과로 현재 수준을 채웠어요. 나머지 칸을 채워 주세요.</Message>
      <Message v-if="fromAi" severity="info" class="mb-3">AI가 채운 초안이에요. 학습 목적은 AI 추천값이에요. 틀린 칸을 고친 뒤 저장해 주세요.</Message>
      <Message v-for="(w, i) in warnings" :key="i" severity="warn" class="mb-2">{{ w }}</Message>
      <ErrorBox :error="error" @retry="draft" />
      <StudentForm :model-value="form" :saving="saving" submit-label="저장" @submit="save" @cancel="router.back()" />
    </section>
  </div>
</template>
