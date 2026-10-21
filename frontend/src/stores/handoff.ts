import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { IntakeResult } from '../api/types'

/** 채팅에서 만든 초안을 다른 화면으로 넘겨줄 때 쓰는 임시 보관함 (학생 등록 초안, 수업 메모) */
export const useHandoffStore = defineStore('handoff', () => {
  const intake = ref<IntakeResult | null>(null)
  const notes = ref<Record<number, string>>({})

  function takeIntake() {
    const value = intake.value
    intake.value = null
    return value
  }

  function takeNote(lessonId: number) {
    const value = notes.value[lessonId]
    delete notes.value[lessonId]
    return value
  }

  return { intake, notes, takeIntake, takeNote }
})
