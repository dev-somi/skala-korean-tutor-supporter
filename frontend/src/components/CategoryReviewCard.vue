<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { CATEGORY_NAMES, type Category, type CategoryDraft, type Decision } from '../api/types'
import ItemChips from './ItemChips.vue'

// 범주 하나의 초안을 보여 주고, 선생님 결정(승인 / 직접 수정 / 피드백)을 받는다 (PRD F3-3)
const props = defineProps<{ category: Category; draft: CategoryDraft; approved: boolean; decision: Decision }>()
const emit = defineEmits<{ 'update:decision': [Decision] }>()

const options = [
  { label: '승인', value: 'approve', icon: 'pi pi-check' },
  { label: '직접 수정', value: 'edit', icon: 'pi pi-pencil' },
  { label: '피드백', value: 'feedback', icon: 'pi pi-comment' },
]

const action = computed({
  get: () => props.decision.action,
  set: value => {
    const next: Decision = { action: value }
    if (value === 'edit') Object.assign(next, { explanation: props.draft.explanation, script: props.draft.script })
    if (value === 'feedback') next.feedback = props.decision.feedback ?? ''
    emit('update:decision', next)
  },
})

function patch(field: 'explanation' | 'script' | 'feedback', value: string | undefined) {
  emit('update:decision', { ...props.decision, [field]: value ?? '' })
}
</script>

<template>
  <Card :class="approved ? 'opacity-80' : ''">
    <template #title>
      <div class="flex flex-wrap items-center gap-2">
        <span>{{ CATEGORY_NAMES[category] }}</span>
        <Tag :value="draft.minutes + '분'" severity="secondary" />
        <Tag v-if="approved" value="확정됨" severity="success" icon="pi pi-lock" />
      </div>
    </template>
    <template #subtitle>
      <ItemChips :ids="draft.item_ids" empty="(교재 항목 없음)" />
      <p class="mb-0 mt-2 text-sm">{{ draft.reason }}</p>
    </template>
    <template #content>
      <div class="grid gap-4 lg:grid-cols-2">
        <section>
          <h4 class="mb-1 mt-0 text-sm font-bold text-surface-600">개인화 설명</h4>
          <Textarea
            v-if="decision.action === 'edit' && !approved"
            :model-value="decision.explanation"
            rows="8"
            auto-resize
            class="w-full"
            @update:model-value="v => patch('explanation', v)"
          />
          <div v-else class="pre-line rounded-lg bg-surface-50 p-3 text-sm leading-relaxed">{{ draft.explanation }}</div>
          <ul v-if="draft.examples.length" class="mb-0 mt-2 space-y-1 pl-5 text-sm">
            <li v-for="(ex, i) in draft.examples" :key="i">
              {{ ex.korean }}
              <Tag v-if="ex.is_new" value="새 예문" severity="warn" class="ml-1 !text-[0.7rem]" />
            </li>
          </ul>
        </section>
        <section>
          <h4 class="mb-1 mt-0 text-sm font-bold text-surface-600">수업 대본</h4>
          <Textarea
            v-if="decision.action === 'edit' && !approved"
            :model-value="decision.script"
            rows="8"
            auto-resize
            class="w-full"
            @update:model-value="v => patch('script', v)"
          />
          <div v-else class="pre-line max-h-72 overflow-y-auto rounded-lg bg-surface-50 p-3 text-sm leading-relaxed">{{ draft.script }}</div>
        </section>
      </div>
    </template>
    <template v-if="!approved" #footer>
      <div class="flex flex-col gap-2">
        <SelectButton v-model="action" :options="options" option-label="label" option-value="value" :allow-empty="false">
          <template #option="{ option }"><i :class="option.icon" class="mr-1" />{{ option.label }}</template>
        </SelectButton>
        <Textarea
          v-if="decision.action === 'feedback'"
          :model-value="decision.feedback"
          rows="2"
          auto-resize
          placeholder="이 범주를 어떻게 고치면 좋을지 적어 주세요. 예) 숙제를 더 짧게"
          @update:model-value="v => patch('feedback', v)"
        />
      </div>
    </template>
  </Card>
</template>
