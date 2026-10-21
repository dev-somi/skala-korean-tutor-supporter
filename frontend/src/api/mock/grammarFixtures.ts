// 채팅 mock 시나리오 (기술 ADR-0027). fixtures/*.json 은 2026-10-21 로컬 ai-server POST /grammar-qa 응답을 그대로 저장한 것이다.
// RAG가 응답 모양을 바꾸면 여기와 api/types.ts 의 채팅 SSE 계약을 먼저 고친다.
import type { ChatRouting, GrammarQaResult } from '../types'
import compare from './fixtures/compare-aseo-nikka.json'
import outOfLevel from './fixtures/student-out-of-level.json'
import ungrounded from './fixtures/ungrounded.json'

export interface MockScenario {
  name: string
  /** 질문에 이 글자들 중 하나가 있으면 이 시나리오 */
  match: string[]
  routing: ChatRouting
  grammar?: GrammarQaResult
  /** grammar_qa가 아닐 때 token으로 보낼 글 */
  text?: string
  error?: { code: string; message: string; retryable: boolean }
}

const grammarRouting = (student_name: string | null = null): ChatRouting => ({
  intent: 'grammar_qa',
  student_id: student_name ? 1 : null,
  student_name,
  reason: '문법 차이를 묻는 질문',
})

// grammar_qa.py answer_question 의 "형태를 못 찾음" 반환값
const notFound: GrammarQaResult = {
  points: ["어떤 문법을 묻는지 찾지 못했어요. '-아서', '은/는'처럼 형태를 적어서 다시 물어봐 주세요."],
  ai_note: '',
  removed_points: [],
  forms: [],
  out_of_level: [],
  ungrounded_forms: [],
  grounded: false,
}

export const SCENARIOS: MockScenario[] = [
  { name: '오류', match: ['오류', 'error'], routing: grammarRouting(), error: { code: 'AI_SERVER_UNAVAILABLE', message: 'ai-server에 연결할 수 없습니다 (mock)', retryable: true } },
  { name: '등급 밖', match: ['살던', '사는', '유이'], routing: grammarRouting('유이'), grammar: outOfLevel as GrammarQaResult },
  { name: '근거 없음', match: ['더라고요', '근거 없'], routing: grammarRouting(), grammar: ungrounded as GrammarQaResult },
  { name: '형태 못 찾음', match: ['이거', '그거', '어떻게 가르쳐'], routing: grammarRouting(), grammar: notFound },
  { name: '근거 충분', match: ['-아서', '니까', '-'], routing: grammarRouting(), grammar: compare as GrammarQaResult },
]

export const GENERAL: MockScenario = {
  name: '일반 질문',
  match: [],
  routing: { intent: 'general', student_id: null, student_name: null, reason: '일반 질문' },
  text: 'mock 응답이에요. 문법 차이를 물어보면(예: "-아서랑 -(으)니까 뭐가 달라?") 교재 근거 카드가 붙은 답을 볼 수 있어요.',
}

export function pickScenario(message: string): MockScenario {
  return SCENARIOS.find(s => s.match.some(m => message.includes(m))) ?? GENERAL
}
