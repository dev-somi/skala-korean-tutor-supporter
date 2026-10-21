<script setup lang="ts">
// 다음 수업 준비 폼: 수업을 만들고 검토 화면으로 간다 (그 화면에서 준비가 자동으로 시작됨).
// studentId를 주면 학생이 고정되고, 없으면 학생을 고른다 (수업 준비 탭, 기술 ADR-0029).
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import ErrorBox from './ErrorBox.vue'
import { lessonsApi, studentsApi } from '../api/endpoints'
import { LANG_NAMES, levelName, type StudentSummary } from '../api/types'
import { toUiError, type UiError } from '../utils'

const props = defineProps<{ studentId?: number | null; students?: StudentSummary[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const router = useRouter()

const selected = ref<number | null>(null)
const form = ref({ unitNo: 1, minutes: 50, targetLang: 'ja' as 'ja' | 'en', lessonDate: null as Date | null })
const creating = ref(false)
const error = ref<UiError | null>(null)
const langOptions = [
  { label: '일본어', value: 'ja' },
  { label: '영어', value: 'en' },
]
const studentLabel = (s: StudentSummary) => `${s.name} · ${LANG_NAMES[s.nativeLanguage]} · ${levelName(s.standardLevel)} · 다음 ${s.nextUnit}과`

// 학생을 고르면 그 학생의 다음 과·기본 시간·모국어로 채운다
async function fill(id: number | null) {
  error.value = null
  if (id == null) return
  try {
    const s = await studentsApi.get(id)
    form.value = { unitNo: s.nextUnit, minutes: s.lessonMinutesDefault, targetLang: s.nativeLanguage, lessonDate: null }
  } catch (e) {
    error.value = toUiError(e)
  }
}

watch(visible, open => {
  if (!open) return
  selected.value = props.studentId ?? null
  fill(selected.value)
}, { immediate: true })

async function create() {
  if (selected.value == null) return
  creating.value = true
  try {
    const f = form.value
    const d = f.lessonDate
    const lessonDate = d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` : undefined
    const lesson = await lessonsApi.create(selected.value, { unitNo: f.unitNo, minutes: f.minutes, targetLang: f.targetLang, lessonDate })
    router.push(`/lessons/${lesson.id}/review`)
  } catch (e) {
    error.value = toUiError(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" header="다음 수업 준비" modal class="w-full max-w-md">
    <ErrorBox :error="error" />
    <div class="grid gap-3">
      <label v-if="studentId == null" class="flex flex-col gap-1 text-sm font-semibold">학생
        <Select v-model="selected" :options="students ?? []" :option-label="studentLabel" option-value="id" placeholder="학생을 고르세요" filter @change="fill(selected)" />
      </label>
      <label class="flex flex-col gap-1 text-sm font-semibold">과 <InputNumber v-model="form.unitNo" :min="1" show-buttons /></label>
      <label class="flex flex-col gap-1 text-sm font-semibold">수업 시간 (분) <InputNumber v-model="form.minutes" :min="10" :max="180" :step="10" show-buttons /></label>
      <label class="flex flex-col gap-1 text-sm font-semibold">설명 언어 <Select v-model="form.targetLang" :options="langOptions" option-label="label" option-value="value" /></label>
      <label class="flex flex-col gap-1 text-sm font-semibold">수업일 (선택) <DatePicker v-model="form.lessonDate" date-format="yy-mm-dd" show-icon /></label>
    </div>
    <template #footer>
      <Button label="취소" severity="secondary" text @click="visible = false" />
      <Button label="준비 시작" icon="pi pi-play" :loading="creating" :disabled="selected == null" @click="create" />
    </template>
  </Dialog>
</template>
