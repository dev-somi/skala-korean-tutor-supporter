import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '../api/endpoints'
import type { ChatAction, ChatRouting, GrammarSources } from '../api/types'

export type { ChatAction, GrammarForm, GrammarSource, GrammarSources } from '../api/types'

/** 답을 기다리는 동안 보여 줄 단계. 문법 질문은 RAG 검색이 길어서 단계를 나눠 보여 준다 */
export type ChatStage = 'routing' | 'searching' | 'writing' | 'answering'

export const STAGE_NAMES: Record<ChatStage, string> = {
  routing: '질문 분류 중',
  searching: '교재에서 근거 찾는 중',
  writing: '요점 정리 중',
  answering: '답 쓰는 중',
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  intent?: string
  studentName?: string | null
  actions: ChatAction[]
  sources?: GrammarSources
  error?: { message: string; retryable: boolean }
  pending?: boolean
  stage?: ChatStage
  /** 이 답을 만든 질문 (다시 보내기용) */
  question?: string
}

export const INTENT_NAMES: Record<string, string> = {
  lookup: '조회',
  student_upsert: '학생 등록',
  lesson_prep: '수업 준비',
  post_lesson: '수업 후 기록',
  grammar_qa: '문법 질문',
  general: '일반 질문',
}

const newConversationId = () => 'c' + Math.random().toString(36).slice(2, 10)

export const useChatStore = defineStore('chat', () => {
  const open = ref(false)
  const messages = ref<ChatMessage[]>([])
  const busy = ref(false)
  let conversationId = newConversationId()
  let controller: AbortController | null = null

  async function send(text: string) {
    if (!text.trim() || busy.value) return
    messages.value.push({ role: 'user', text, actions: [] })
    messages.value.push({ role: 'assistant', text: '', actions: [], pending: true, stage: 'routing', question: text })
    // reactive 프록시를 통해 고쳐야 화면이 바로 바뀐다
    const reply = messages.value[messages.value.length - 1]
    busy.value = true
    controller = new AbortController()
    try {
      await chatApi.stream(
        text,
        conversationId,
        (event, data) => {
          if (event === 'routing_decided') {
            const routing = data as ChatRouting
            reply.intent = routing.intent
            reply.studentName = routing.student_name
            reply.stage = routing.intent === 'grammar_qa' ? 'searching' : 'answering'
          } else if (event === 'token') {
            reply.text += data.text
          } else if (event === 'sources') {
            reply.sources = data as GrammarSources
            reply.stage = 'writing'
          } else if (event === 'action') {
            reply.actions.push(data as ChatAction)
          } else if (event === 'error') {
            reply.error = { message: data.message, retryable: data.retryable }
          }
        },
        controller.signal,
      )
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        if (!reply.text) reply.text = '(중단했어요)'
      } else {
        reply.error = { message: (e as Error).message, retryable: true }
      }
    } finally {
      reply.pending = false
      busy.value = false
      controller = null
    }
  }

  function stop() {
    controller?.abort()
  }

  /** 오류 난 답을 지우고 같은 질문을 다시 보낸다 */
  async function retry(index: number) {
    const question = messages.value[index]?.question
    if (!question || busy.value) return
    messages.value.splice(index - 1, 2)
    await send(question)
  }

  function reset() {
    stop()
    messages.value = []
    conversationId = newConversationId()
  }

  return { open, messages, busy, send, stop, retry, reset }
})
