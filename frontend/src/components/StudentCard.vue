<script setup lang="ts">
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import { LANG_NAMES, PERSONA_NAMES, levelName, type StudentSummary, bookName } from '../api/types'
import { formatDate } from '../utils'

// 학생 프로필 카드. 누르면 학생 상세(프로필 보기·수정)로 간다. 대시보드와 [학생] 메뉴에서 같이 쓴다.
defineProps<{ student: StudentSummary }>()
</script>

<template>
  <RouterLink :to="`/students/${student.id}`" class="no-underline">
    <Card class="h-full !shadow-sm transition hover:!shadow-md" :class="student.status === 'paused' ? 'opacity-60' : ''">
      <template #title>
        <div class="flex items-center gap-2 text-base">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-50 font-bold text-primary-700">{{ student.name.slice(0, 1) }}</span>
          {{ student.name }}
          <Tag :value="LANG_NAMES[student.nativeLanguage]" severity="secondary" />
          <Tag v-if="student.status === 'paused'" value="쉬는 중" severity="contrast" />
        </div>
      </template>
      <template #subtitle>
        <span :class="student.standardLevel == null ? 'text-orange-600' : ''">{{ levelName(student.standardLevel) }}</span>
        <span v-if="student.persona"> · {{ PERSONA_NAMES[student.persona] }}</span>
      </template>
      <template #content>
        <div class="space-y-1 text-sm">
          <div><span class="text-surface-500">다음 과</span> {{ bookName(student.nextBook) }} {{ student.nextUnit }}과 · <span class="text-surface-500">마지막 수업</span> {{ formatDate(student.lastLessonDate) }}</div>
          <div class="flex flex-wrap gap-1">
            <Tag v-for="w in student.mainWeaknesses" :key="w" :value="w" severity="warn" class="!text-xs" />
            <span v-if="!student.mainWeaknesses.length" class="text-surface-400">약점 기록 없음</span>
          </div>
        </div>
      </template>
    </Card>
  </RouterLink>
</template>
