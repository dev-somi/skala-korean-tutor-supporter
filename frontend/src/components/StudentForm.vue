<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import {
  ITEM_ID_PATTERN, PERSONA_NAMES, PERSONA_TEXTBOOKS, STANDARD_LEVELS, levelName,
  type Persona, type StudentRequest, type Weakness,
} from '../api/types'
import { linesToList, listToLines } from '../utils'

const props = defineProps<{ modelValue: StudentRequest; saving?: boolean; submitLabel?: string }>()
const emit = defineEmits<{ submit: [StudentRequest]; cancel: [] }>()

// 목록 칸(목표·관심사)은 한 줄에 하나씩 입력받는다
// props는 reactive 프록시라 structuredClone이 안 된다 → JSON으로 깊은 복사
const copy = (v: StudentRequest): StudentRequest => JSON.parse(JSON.stringify(v))
const form = ref<StudentRequest>(copy(props.modelValue))
const goals = ref(listToLines(form.value.goals))
// 날짜 입력은 빈 문자열을 주므로 null과 바꿔 담는다
const assessedOn = computed({
  get: () => form.value.levelAssessedOn ?? '',
  set: v => (form.value.levelAssessedOn = v || null),
})
const interests = ref(listToLines(form.value.interests))
watch(
  () => props.modelValue,
  v => {
    form.value = copy(v)
    goals.value = listToLines(v.goals)
    interests.value = listToLines(v.interests)
  },
)

const langOptions = [
  { label: '일본어 (ja)', value: 'ja' },
  { label: '영어 (en)', value: 'en' },
]
const levelOptions = STANDARD_LEVELS.map(n => ({ label: levelName(n), value: n }))
const targetOptions = STANDARD_LEVELS.filter(n => n > 0).map(n => ({ label: levelName(n), value: n }))
const personaOptions = (Object.keys(PERSONA_NAMES) as Persona[]).map(p => ({ label: PERSONA_NAMES[p], value: p }))
const statusOptions = [
  { label: '수업 중', value: 'active' },
  { label: '쉬는 중', value: 'paused' },
]

function addWeakness() {
  form.value.weaknesses.push({ id: null, itemId: null, description: '', resolved: false })
}
function removeWeakness(w: Weakness) {
  form.value.weaknesses = form.value.weaknesses.filter(x => x !== w)
}

const invalidIds = computed(() => form.value.weaknesses.filter(w => w.itemId && !ITEM_ID_PATTERN.test(w.itemId)))
const valid = computed(
  () =>
    form.value.name.trim() &&
    form.value.nativeLanguage &&
    form.value.standardLevel != null && // 현재 수준은 필수 (기획 ADR-0018)
    !invalidIds.value.length &&
    form.value.weaknesses.every(w => w.description.trim()),
)

function submit() {
  emit('submit', {
    ...form.value,
    goals: linesToList(goals.value),
    interests: linesToList(interests.value),
    weaknesses: form.value.weaknesses.map(w => ({ ...w, itemId: w.itemId?.trim() || null })),
  })
}
</script>

<template>
  <form class="grid gap-4 md:grid-cols-2" @submit.prevent="submit">
    <label class="field">
      <span>이름 (가명) *</span>
      <InputText v-model="form.name" />
    </label>
    <label class="field">
      <span>모국어 *</span>
      <Select v-model="form.nativeLanguage" :options="langOptions" option-label="label" option-value="value" placeholder="고르세요" />
    </label>
    <label class="field">
      <span>현재 수준 (지금 배울 등급) *</span>
      <Select v-model="form.standardLevel" :options="levelOptions" option-label="label" option-value="value" placeholder="레벨테스트 결과로 고르세요" :invalid="form.standardLevel == null" />
      <small class="text-surface-500">
        국립국어원 표준 교육과정 등급. 모르면
        <RouterLink to="/level-test" target="_blank">레벨테스트</RouterLink>로 확인해요.
      </small>
    </label>
    <label class="field">
      <span>레벨테스트 날짜</span>
      <InputText v-model="assessedOn" type="date" />
    </label>
    <label class="field md:col-span-2">
      <span>수준 세부 메모</span>
      <InputText v-model="form.level" placeholder="예: 한글 읽기 가능, 받침 발음 약함, -아요는 들어 봤음" />
    </label>
    <label class="field">
      <span>목표 수준</span>
      <Select v-model="form.targetLevel" :options="targetOptions" option-label="label" option-value="value" placeholder="없음" show-clear />
    </label>
    <label class="field">
      <span>학습 목적 (중심 교재를 정해요)</span>
      <Select v-model="form.persona" :options="personaOptions" option-label="label" option-value="value" placeholder="고르세요" show-clear />
      <small v-if="form.persona" class="text-surface-500">
        중심 교재: {{ PERSONA_TEXTBOOKS[form.persona] }} · 지금 진도 데이터는 「세종학당 한국어 1」만 있어요
      </small>
    </label>
    <label class="field">
      <span>목표 (한 줄에 하나)</span>
      <Textarea v-model="goals" rows="3" auto-resize />
    </label>
    <label class="field">
      <span>관심사 (한 줄에 하나, 예문 개인화에 씀)</span>
      <Textarea v-model="interests" rows="3" auto-resize />
    </label>
    <label class="field">
      <span>다음에 배울 과</span>
      <InputNumber v-model="form.nextUnit" :min="1" show-buttons />
    </label>
    <label class="field">
      <span>기본 수업 시간 (분)</span>
      <InputNumber v-model="form.lessonMinutesDefault" :min="10" :max="180" :step="10" show-buttons />
    </label>
    <label class="field">
      <span>상태</span>
      <Select v-model="form.status" :options="statusOptions" option-label="label" option-value="value" />
    </label>

    <div class="field md:col-span-2">
      <span>약점 (교재 항목 ID는 있으면 적고, 없으면 설명만)</span>
      <div v-for="(w, i) in form.weaknesses" :key="w.id ?? 'new' + i" class="flex flex-wrap items-center gap-2">
        <InputText :model-value="w.itemId ?? ''" placeholder="u03-g02" @update:model-value="v => (w.itemId = v || null)" class="w-28" :invalid="!!w.itemId && !ITEM_ID_PATTERN.test(w.itemId)" />
        <InputText v-model="w.description" placeholder="예: 받침 발음" class="min-w-48 flex-1" :invalid="!w.description.trim()" />
        <label class="flex items-center gap-1 text-sm"><Checkbox v-model="w.resolved" binary /> 해결됨</label>
        <Button icon="pi pi-trash" severity="secondary" text aria-label="약점 삭제" @click="removeWeakness(w)" />
      </div>
      <div><Button label="약점 추가" icon="pi pi-plus" size="small" severity="secondary" outlined @click="addWeakness" /></div>
      <small v-if="invalidIds.length" class="text-red-600">교재 항목 ID는 u03-g02 같은 모양이어야 해요.</small>
    </div>

    <label class="field md:col-span-2">
      <span>자유 메모 (성격, 수업 스타일, 일정 등)</span>
      <Textarea v-model="form.notes" rows="3" auto-resize />
    </label>

    <div class="flex gap-2 md:col-span-2">
      <Button type="submit" :label="submitLabel ?? '저장'" icon="pi pi-check" :loading="saving" :disabled="!valid" />
      <Button label="취소" severity="secondary" text @click="$emit('cancel')" />
    </div>
  </form>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.field > span {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-surface-600);
}
</style>
