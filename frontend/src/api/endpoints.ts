import { del, get, post, put } from './http'
import { streamSse, type SseHandler } from './sse'
import type {
  ApproveRequest, Category, CurriculumBook, Decision, IntakeResult, LessonView, LevelTest, LevelTestResult, LevelTestScore, MaterialOpenResult, PrepState, ProgressReport, QualityMetrics, RecordView,
  StandardGrammar, StandardList, StandardVocab, TextbookItem,
  StudentDetail, StudentRequest, StudentSummary, TimeMetrics, Todos, TraceDetail, TraceList,
} from './types'

export const studentsApi = {
  list: () => get<StudentSummary[]>('/students'),
  get: (id: number) => get<StudentDetail>(`/students/${id}`),
  create: (body: StudentRequest) => post<StudentDetail>('/students', body),
  update: (id: number, body: StudentRequest) => put<StudentDetail>(`/students/${id}`, body),
  remove: (id: number) => del(`/students/${id}`),
  intake: (text: string) => post<IntakeResult>('/students/intake', { text }),
  report: (id: number, from?: string, to?: string) => {
    const q = new URLSearchParams()
    if (from) q.set('from', from)
    if (to) q.set('to', to)
    const query = q.toString()
    return get<ProgressReport>(`/students/${id}/report${query ? `?${query}` : ''}`)
  },
}

export const levelTestApi = {
  get: () => get<LevelTest>('/level-test'),
  score: (answers: Record<string, boolean>) => post<LevelTestScore>('/level-test/score', { answers }),
  save: (answers: Record<string, boolean>, note: string) => post<LevelTestResult>('/level-test/results', { answers, note }),
  result: (id: number) => get<LevelTestResult>(`/level-test/results/${id}`),
  apply: (id: number, studentId: number, level?: number) => post<LevelTestResult>(`/level-test/results/${id}/apply`, { studentId, level }),
  dismiss: (id: number) => post<LevelTestResult>(`/level-test/results/${id}/dismiss`, {}),
}

/** 빈 값은 빼고 쿼리 문자열로 */
const qs = (params: Record<string, string | number | null | undefined>) => {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') q.set(k, String(v))
  const s = q.toString()
  return s ? `?${s}` : ''
}

// 교재 항목 ID → 화면에 보일 이름 (기술 ADR-0029)
export const textbookApi = {
  items: () => get<{ items: Record<string, TextbookItem> }>('/textbook/items'),
}

export const standardApi = {
  grammar: (params: { level?: number | null; category?: string | null; q?: string }) => get<StandardList<StandardGrammar>>(`/standard/grammar${qs(params)}`),
  vocab: (params: { level?: number | null; pos?: string | null; q?: string; offset?: number; limit?: number }) =>
    get<StandardList<StandardVocab>>(`/standard/vocab${qs(params)}`),
}

/** 단원 시트 목록 (기술 ADR-0032) */
export const curriculumApi = {
  list: () => get<{ books: CurriculumBook[] }>('/curriculum'),
}

/** 교재 원본 PDF (기술 ADR-0030): 로컬 ai-server가 선생님 컴퓨터의 PDF를 그 쪽으로 연다 */
export const materialsApi = {
  list: () => get<{ books: string[] }>('/materials'),
  open: (book: string, page: number) => post<MaterialOpenResult>('/materials/open', { book, page }),
}

export const lessonsApi = {
  listByStudent: (studentId: number) => get<LessonView[]>(`/students/${studentId}/lessons`),
  create: (studentId: number, body: { book?: string; unitNo?: number; minutes?: number; targetLang?: string; lessonDate?: string } = {}) =>
    post<LessonView>(`/students/${studentId}/lessons`, body),
  get: (id: number) => get<LessonView>(`/lessons/${id}`),
  prepState: (id: number) => get<PrepState>(`/lessons/${id}/prep/state`),
  startPrep: (id: number, onEvent: SseHandler, signal?: AbortSignal) => streamSse(`/lessons/${id}/prep`, {}, onEvent, signal),
  review: (id: number, decisions: Partial<Record<Category, Decision>>, onEvent: SseHandler, signal?: AbortSignal) =>
    streamSse(`/lessons/${id}/prep/review`, { decisions }, onEvent, signal),
  fileUrl: (id: number, kind: 'pptx' | 'pdf') => `/api/lessons/${id}/files/${kind}`,
}

export const recordsApi = {
  get: (lessonId: number) => get<RecordView>(`/lessons/${lessonId}/record`),
  draft: (lessonId: number, rawNote: string, noteStartedAt: string | null, onEvent: SseHandler, signal?: AbortSignal) =>
    streamSse(`/lessons/${lessonId}/record`, { rawNote, noteStartedAt }, onEvent, signal),
  approve: (lessonId: number, body: ApproveRequest) => post<RecordView>(`/lessons/${lessonId}/record/approve`, body),
}

export const dashboardApi = {
  todos: () => get<Todos>('/dashboard/todos'),
  metrics: () => get<TimeMetrics>('/metrics/time'),
  quality: () => get<QualityMetrics>('/metrics/quality'),
  saveBaseline: (kind: 'prep' | 'post', minutes: number, note: string, isEstimate: boolean) =>
    put(`/baselines/${kind}`, { minutes, note, isEstimate }),
}

/** 개발 중 주소에 ?mock 이 있으면 채팅만 가짜 스트림을 쓴다 (기술 ADR-0027). 프로덕션 빌드에서는 false로 바뀌어 mock 코드가 빠진다 */
export const CHAT_MOCK = import.meta.env.DEV && new URLSearchParams(location.search).has('mock')

export const chatApi = {
  stream: async (message: string, conversationId: string, onEvent: SseHandler, signal?: AbortSignal) => {
    if (import.meta.env.DEV && CHAT_MOCK) {
      const { mockStream } = await import('./mock/chatMock')
      return mockStream(message, onEvent, signal)
    }
    return streamSse('/chat/stream', { message, conversationId }, onEvent, signal)
  },
}

/** AI 추적 (LangSmith 실행 기록, 기술 ADR-0028) */
export const tracesApi = {
  list: (params: { limit?: number; name?: string | null; errorsOnly?: boolean }) =>
    get<TraceList>(`/traces${qs({ limit: params.limit, name: params.name, errorsOnly: params.errorsOnly ? 'true' : null })}`),
  get: (traceId: string) => get<TraceDetail>(`/traces/${traceId}`),
}
