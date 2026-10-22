// backend(Spring) API 모양.
// REST 응답의 필드는 camelCase, AI가 만든 JSON(plan, briefing, drafts, 기록 초안, SSE data)은 ai-server 그대로 snake_case.

export type Lang = 'ja' | 'en'
export type Category = 'review' | 'new_vocab' | 'new_grammar' | 'homework'

// shared/constraints.json 과 같아야 한다
export const CATEGORIES: Category[] = ['review', 'new_vocab', 'new_grammar', 'homework']
export const CATEGORY_NAMES: Record<Category, string> = {
  review: '복습 내용',
  new_vocab: '새로운 어휘',
  new_grammar: '새로운 문법',
  homework: '숙제 내용',
}
export const LANG_NAMES: Record<Lang, string> = { ja: '일본어', en: '영어' }

// 표준 등급: 0 = 입문(한글부터), 1~6 = 국립국어원 표준 교육과정 N급 (기획 ADR-0016, ADR-0018)
export const STANDARD_LEVELS = [0, 1, 2, 3, 4, 5, 6] as const
export const levelName = (n: number | null | undefined) =>
  n == null ? '수준 미정' : n === 0 ? '입문 (한글부터)' : `표준 ${n}급`

export type Persona = 'structured' | 'conversation' | 'travel' | 'business'
export const PERSONA_NAMES: Record<Persona, string> = {
  structured: '체계적 학습 · TOPIK 준비',
  conversation: '일상 회화 (드라마 · K-콘텐츠 포함)',
  travel: '여행',
  business: '업무',
}
// 페르소나가 중심 교재를 정한다. 지금 진도 데이터가 있는 교재는 「한국어 1」뿐이다
export const PERSONA_TEXTBOOKS: Record<Persona, string> = {
  structured: '세종학당 한국어 1~6 (한글이 처음이면 입문부터)', // 기획 ADR-0022
  conversation: '세종학당 실용 한국어 1~2',
  travel: '여행 한국어',
  business: '비즈니스 한국어 1~2',
}
// shared/constraints.json 의 item_id_pattern: 표준 ID(std-g-007), 교재 안 ID(ko1-u02-d01), 옛 교재 ID(u02-g01) (기술 ADR-0032)
export const ITEM_ID_PATTERN = /^(std-[gv]-\d{3,5}|[a-z0-9]+-u\d{2}-[vgdrex]\d{2}|u\d{2}-[vgdre]\d{2})$/
export const LESSON_STATUS_NAMES: Record<string, string> = {
  planned: '준비 전',
  prepared: '수업안 확정',
  done: '수업함 (기록 미승인)',
  recorded: '기록 완료',
}

export interface Weakness {
  id?: number | null
  itemId?: string | null
  description: string
  resolved?: boolean
  // 응답 전용
  sinceLessonId?: number | null
  createdAt?: string
  resolvedAt?: string | null
}

export interface StudentRequest {
  name: string
  nativeLanguage: Lang
  level: string // 수준 세부 메모
  standardLevel: number | null // 저장할 때는 필수 (null은 아직 안 고른 것)
  targetLevel: number | null
  levelAssessedOn: string | null // YYYY-MM-DD
  persona: Persona | null
  goals: string[]
  interests: string[]
  /** 다음에 배울 교재 시리즈 (ko1, ko2). 비우면 서버가 그대로 둔다 */
  nextBook?: string
  nextUnit: number
  lessonMinutesDefault: number
  notes: string
  status: 'active' | 'paused'
  weaknesses: Weakness[]
}

export interface StudentDetail extends StudentRequest {
  id: number
  createdAt: string
  updatedAt: string
}

export interface StudentSummary {
  id: number
  name: string
  nativeLanguage: Lang
  level: string
  standardLevel: number | null
  persona: Persona | null
  nextBook: string
  nextUnit: number
  status: string
  lastLessonDate: string | null
  mainWeaknesses: string[]
}

export interface IntakeDraft {
  name: string | null
  native_language: Lang | null
  level: string | null
  standard_level: number | null
  target_level: number | null
  persona: Persona | null
  goals: string[]
  interests: string[]
  weaknesses: { item_id: string | null; description: string }[]
  next_unit: number | null
  lesson_minutes_default: number | null
  notes: string
}

export interface IntakeResult {
  draft: IntakeDraft
  warnings: string[]
}

export interface CategoryPlan {
  item_ids: string[]
  minutes: number
  reason: string
}

export interface CategoryDraft extends CategoryPlan {
  explanation: string
  examples: { korean: string; is_new: boolean }[]
  script: string
}

/** 슬라이드 레이아웃 5가지 (기준 문서 §5) */
export const SLIDE_LAYOUT_NAMES: Record<string, string> = {
  question: '질문·도입',
  vocab: '어휘',
  expression: '표현 설명',
  practice: '연습·활동',
  closing: '피드백·마무리',
}

/** 슬라이드 하나의 교사용 발표자 노트 (소요 시간은 슬라이드의 minutes) */
export interface SlideNote {
  goal: string
  procedure: string
  qa: { question: string; answer: string }[]
  if_struggle: string
  if_good: string
  source: string
}

/** 장별 대본의 한 줄 (기획 ADR-0033). teacher = 선생님이 읽는 말, student_expected = 학생이 할 법한 답 */
export interface ScriptLine {
  who: 'teacher' | 'student_expected'
  ko: string
  hint: string
  wait: boolean
}

export interface SlideScript {
  lines: ScriptLine[]
  transition: string
  fallback: ScriptLine[]
}

/** 15장 슬라이드 구성안의 한 장 (기획 ADR-0032). 번호·단계·시간은 코드, 문구와 노트는 LLM */
export interface Slide {
  no: number
  stage: string
  name: string
  layout: string
  minutes: number
  categories: Category[]
  student_screen: string[]
  activity: string
  note: SlideNote
  needs_check: string[]
  /** 수업에서 읽을 대본. 예전 수업이나 생성에 실패한 장은 없다 */
  script?: SlideScript | null
}

export interface SlidePlan {
  lesson_goal: string
  final_mission: string
  slides: Slide[]
  homework: { pages: string; items: string; how: string; example: string }
  needs_check: string[]
  checks: { name: string; passed: boolean; reason: string }[]
}

/** (예전 수업) 고정된 7단계 수업 틀의 한 단계 (기획 ADR-0015). slide_plan이 없는 수업만 쓴다 */
export interface FrameStep {
  key: string
  name: string
  minutes: number
  guide: string
  categories: Category[]
  items: string[]
  /** 새 내용 도입 단계만: briefing.culture 중 기본으로 고른 후보 번호. null = 자료에서 못 찾음 */
  culture?: number | null
}

/** 세종학당 자료에서 찾은 문화 포인트 (기획 ADR-0023). 출처·원문은 코드, 요약·질문은 LLM */
export interface CultureNote {
  book: string
  pages?: number[]
  source: string
  excerpt: string
  summary: string
  question_ko: string
  question_l1: string
}

export interface Briefing {
  grammar_points: { item_id: string; key_points: string[] }[]
  common_mistakes: string[]
  expected_qa: { question: string; answer: string }[]
  tips: string[]
  warmup_questions?: string[]
  practice_activity?: string
  /** 근거로 쓴 교원용 지침서 구역 (코드가 붙인 출처) */
  references?: { source: string; section: string; book?: string; pages?: number[] }[]
  /** 15장 슬라이드 구성안 (기획 ADR-0032) */
  slide_plan?: SlidePlan
  /** (예전 수업) 7단계 수업 틀. slide_plan이 없을 때만 보여 준다 */
  lesson_frame?: FrameStep[]
  /** 모국어 칸(자주 틀리는 점, 예상 질문)의 출처: reviewed = 선생님 검수, draft = Claude 초안, llm = 실행 중 생성 (기술 ADR-0022) */
  l1_sources?: { form: string; origin: 'reviewed' | 'draft' | 'llm' }[]
  /** 이번 과의 단원 시트. draft = 자료에서 자동으로 만듦(검수 전) (기획 ADR-0030) */
  unit_sheet?: { book: string; unit_no: number; status: 'draft' | 'reviewed'; notes: string[] }
  culture?: CultureNote[]
}

export interface LessonView {
  id: number
  studentId: number
  studentName: string
  lessonNo: number
  lessonDate: string | null
  minutes: number
  book: string
  unitNo: number
  targetLang: Lang
  status: 'planned' | 'prepared' | 'done' | 'recorded'
  prepThreadId: string | null
  plan: Record<Category, CategoryPlan> | null
  briefing: Briefing | null
  drafts: Record<Category, CategoryDraft> | null
  coveredItemIds: string[]
  pptxFile: string | null
  pdfFile: string | null
  createdAt: string
  updatedAt: string
}

export interface ReviewCheck {
  name: string
  passed: boolean
  reason: string
  /** code = 정답이 있는 점검(통과 여부를 정함), llm = 참고 의견 (기술 ADR-0021) */
  kind?: 'code' | 'llm'
}

/** 수업 준비 그래프가 선생님 검토에서 멈췄을 때 받는 내용 (review_required 이벤트) */
export interface ReviewPayload {
  thread_id: string
  drafts: Record<Category, CategoryDraft>
  briefing: Briefing | null
  review_result: { checks: ReviewCheck[]; passed: boolean } | null
  review_warning: boolean
  approved_categories: Category[]
}

export interface PrepState extends Partial<ReviewPayload> {
  status: 'review_required' | 'running' | 'done'
}

export type DecisionAction = 'approve' | 'edit' | 'feedback'
export interface Decision {
  action: DecisionAction
  explanation?: string
  script?: string
  feedback?: string
}

export interface LessonError {
  student_said: string
  correction: string
  item_id: string | null
  note: string
}
export interface WeaknessChangeDraft {
  action: 'add' | 'resolve'
  weakness_id: number | null
  item_id: string | null
  description: string
}
export interface HomeworkItem {
  item_id: string | null
  description: string
}
export interface FeedbackMessage {
  target_lang_text: string
  korean_text: string
}

// 다룬 항목별 이해도 (기획 ADR-0029, 기술 ADR-0033): AI가 장면을 인용하고 코드가 판정한다
export type UnderstandingLevel = 'confused' | 'shaky' | 'ok'
export const UNDERSTANDING_NAMES: Record<UnderstandingLevel, string> = { confused: '헷갈림', shaky: '조금 헷갈림', ok: '괜찮음' }
export const EPISODE_NAMES: Record<string, string> = {
  error: '틀림', asked_again: '다시 물어봄', hesitation: '망설임', re_explained: '다시 설명함', self_corrected: '스스로 고침', correct: '바로 맞힘',
}
export interface ItemUnderstanding {
  item_id: string
  level: UnderstandingLevel
  score: number
  episodes: { kind: string; quote: string }[]
}

export interface RecordDraft {
  covered_item_ids: string[]
  understanding?: ItemUnderstanding[] // 이 기능 전에 만든 초안에는 없다
  strengths: string[]
  errors: LessonError[]
  weakness_changes: WeaknessChangeDraft[]
  homework: HomeworkItem[]
  next_lesson_note: string
  feedback_message: FeedbackMessage
  warnings: string[]
  validation: { is_acceptable: boolean; reasoning: string } | null
}

export interface RecordView {
  lessonId: number
  studentId: number
  studentName: string
  lessonNo: number
  rawNote: string
  draft: RecordDraft
  approved: Record<string, unknown> | null
  approvedAt: string | null
  updatedAt: string
}

export interface ApproveRequest {
  coveredItemIds: string[]
  strengths: string[]
  errors: LessonError[]
  weaknessChanges: { action: 'add' | 'resolve'; weaknessId: number | null; itemId: string | null; description: string }[]
  homework: HomeworkItem[]
  nextLessonNote: string
  feedbackMessage: FeedbackMessage
  nextUnit: number | null
  understanding: Record<string, UnderstandingLevel>
}

export interface Todos {
  pendingRecords: RecordView[]
  pendingPrep: LessonView[]
  toRecord: LessonView[]
  pendingLevelTests: LevelTestResult[]
}

export interface Session {
  lessonId: number
  studentId: number
  studentName: string
  startedAt: string
  totalMinutes: number
  aiWaitMinutes: number
  teacherMinutes: number
}

export interface KindSummary {
  kind: 'prep' | 'post'
  sessions: number
  avgTotalMinutes: number | null
  avgAiWaitMinutes: number | null
  avgTeacherMinutes: number | null
  baselineMinutes: number | null
  baselineIsEstimate: boolean
  baselineNote: string | null
  reductionPercent: number | null
  recent: Session[]
}

export type TimeMetrics = Record<'prep' | 'post', KindSummary>

/** SSE 진행 이벤트 (node_finished) */
export interface ProgressEvent {
  node: string
  label: string
}

export interface ApiErrorBody {
  code: string
  message: string
  retryable: boolean
}

// 체험수업 레벨테스트 (ai-server /level-test 그대로, snake_case)
export interface LevelTestWord {
  id: string
  std_id: string
  word: string
  guide: string | null
  pos: string | null
}
export interface LevelTestGrammar {
  id: string
  std_id: string
  form: string
  question: string
  listen_for: string
  example: string
}
export interface LevelTestSection {
  level: number
  name: string
  minutes: number
  grammar: LevelTestGrammar[]
  vocab: LevelTestWord[]
}
export interface LevelTest {
  minutes: number
  pass_ratio: number
  min_answered: number
  how_to: string[]
  review_note: string
  hangul: { instruction: string; pass_min: number; words: LevelTestWord[] }
  levels: LevelTestSection[]
}
export interface LevelTestScore {
  suggested_level: number | null
  suggested_name: string | null
  reason: string
  hangul_correct: number | null
  levels: { level: number; answered: number; correct: number; status: 'passed' | 'failed' | 'not_enough' | 'untested' }[]
}
/** 저장한 레벨테스트 결과 (backend, camelCase. score는 ai-server 판정 그대로). 학생 카드에는 선생님이 확인해야 반영된다 (기획 ADR-0021) */
export interface LevelTestResult {
  id: number
  suggestedLevel: number | null
  score: LevelTestScore
  answered: number
  note: string
  status: 'pending' | 'applied' | 'dismissed'
  studentId: number | null
  appliedLevel: number | null
  takenAt: string
  decidedAt: string | null
}

// 진도·향상 리포트 (ai-server /report/progress 그대로, snake_case, 기획 ADR-0019)
export interface ProgressReport {
  student: { name: string; native_language: Lang; standard_level: number | null; target_level: number | null; next_unit: number | null }
  level_name: string | null
  target_name: string | null
  period: { from: string; to: string }
  lessons: { count: number; minutes: number; total_count: number; units: number[] }
  new: { grammar: { id: string; form: string; level: number }[]; vocab: { word: string; level: number }[] }
  total: { grammar: number; vocab: number }
  coverage: { level: number; name: string; grammar: { learned: number; total: number }; vocab: { learned: number; total: number } }[]
  remaining_to_target: { count: number; next: { id: string; level: number; form: string }[] }
  strengths: string[]
  resolved_weaknesses: string[]
  open_weaknesses: string[]
  repeated_errors: { key: string; count: number; student_said: string; correction: string; item_id: string | null }[]
  messages: Record<string, string> // ko + 학생 언어
}

// 주 지표: AI 초안을 그대로 승인한 비율 (기획 ADR-0020)
export interface Rate {
  total: number
  kept: number
  percent: number | null
}
export interface QualityMetrics {
  prep: Record<'review' | 'new_vocab' | 'new_grammar' | 'homework' | 'all', Rate>
  post: Record<'covered_item_ids' | 'strengths' | 'errors' | 'weakness_changes' | 'homework' | 'all', Rate>
}

// 국립국어원 표준 교육과정 등급 목록 (ai-server /standard 그대로)
export interface StandardSource {
  title: string
  publisher: string
  url: string
  license: string
}
export interface StandardGrammar {
  id: string
  level: number
  category: string | null
  form: string
  homonym: string | null
  has_homonyms: boolean // 같은 글자가 목록에 두 번 이상 있을 때만 true → 이때만 번호를 보여 준다
  related: string[]
  meaning: string | null
  textbook: StandardTextbookLink[]
}
export interface StandardVocab {
  id: string
  level: number
  word: string
  homonym: string | null
  has_homonyms: boolean // 같은 글자가 목록에 두 번 이상 있을 때만 true → 이때만 번호를 보여 준다
  pos: string | null
  guide: string | null
  textbook: StandardTextbookLink[]
}
// 이 표준 항목을 다루는 교재 과 (단원 시트에서 거꾸로 찾음, 기술 ADR-0036)
export interface StandardTextbookLink {
  book: string // ko1, ko2
  title: string // 세종학당 한국어 1
  short: string // 한국어 1
  unit_no: number
  status: 'draft' | 'reviewed' // draft = 선생님 검수 전 시트
}
export interface StandardList<T> {
  source: StandardSource
  total: number
  offset?: number
  categories?: Record<string, number> // 문법만: 분류별 개수 (등급·검색어 기준)
  pos_counts?: Record<string, number> // 어휘만: 품사별 개수 (등급·검색어 기준)
  all_total?: number // 어휘만: 품사 필터 전 개수
  items: T[]
}

// ── 채팅 SSE 계약 (POST /api/chat/stream, 기술 ADR-0006·0027) ──────────────────────
// 프론트·Spring·ai-server가 함께 지키는 모양. 바꾸려면 이 타입과 api/mock/fixtures 를 먼저 고친다.
//   routing_decided  {intent, student_id, student_name, reason, lang}     ChatService.handle
//   sources          GrammarSources (grammar_qa만)                        ChatService.grammarQa ← ai-server /grammar-qa
//   token            {text}                                                답 글 (여러 번 올 수 있다)
//   action           ChatAction                                            작업 의도 → 화면으로 넘김 (ADR-0010)
//   error            {code, message, retryable}
//   done             {}

export type ChatIntent = 'lookup' | 'student_upsert' | 'lesson_prep' | 'post_lesson' | 'grammar_qa' | 'general'

export interface ChatRouting {
  intent: ChatIntent
  student_id: number | null
  student_name: string | null
  reason: string
  /** 이 답에 쓴 설명 언어 (토글 또는 학생 모국어, 기획 ADR-0035) */
  lang?: 'ja' | 'en'
}

/** 채팅 설명 언어 토글. auto = 학생 모국어, 학생이 없으면 일본어 */
export type ChatLang = 'auto' | 'ja' | 'en'

/** 저장된 대화 (GET /api/chat/conversations, 기술 ADR-0041) */
export interface ChatConversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

/** 저장된 메시지. 답의 meta에는 화면에 보였던 태그·근거·버튼이 들어 있다 */
export interface StoredChatMessage {
  id: number
  role: 'user' | 'assistant'
  text: string
  meta: {
    intent?: ChatIntent
    studentName?: string | null
    lang?: 'ja' | 'en'
    sources?: GrammarSources
    actions?: ChatAction[]
    error?: { message: string; retryable: boolean }
  }
  createdAt: string
}

export interface ChatAction {
  type: 'open_intake' | 'open_prep' | 'open_record' | 'open_student'
  label: string
  lesson_id?: number
  student_id?: number
  note?: string
  intake?: unknown
}

/** 문법 질문(grammar_qa)의 교재 근거. ai-server app/agent/grammar_qa.py 의 응답 모양 (PRD F6-4) */
export interface GrammarSource {
  kind: 'handbook' | 'guide' | 'text' // text = 태그 없이 본문 글자로 찾은 구역 (기술 ADR-0044)
  source: string
  /** 원본 PDF를 그 쪽으로 열 때 쓴다 (기술 ADR-0030). 예전에 저장된 응답에는 없다 */
  book?: string
  pages?: number[]
  examples?: string[]
  explain_ko?: string
  explain_native?: string
  native_lang?: 'ja' | 'en' | null
  quote?: string
}

export interface GrammarForm {
  form: string
  key: string // 내부 형태 키 (화면에 보이지 않음, 기술 ADR-0025)
  meaning: string | null
  level: number | null // 표준 목록과 맞지 않으면 null
  /** 비교표 한 줄 (기술 ADR-0043). usage = LLM이 쓴 쓰임 한 줄, example = 코드가 핸드북에서 고른 예문. 예전에 저장된 응답에는 없다 */
  usage?: string
  example?: string
  /** 관련형이면 근거를 찾은 대표형 ("-라서" → "-어서", 기술 ADR-0037) */
  standard_form?: string | null
  /** 교재 근거가 없을 때만: AI가 만든 설명 (기획 ADR-0036). 예문은 AI 예문이라 교재 예문 칸에 넣지 않는다 */
  ai?: { usage: string; explanation: string; examples: string[]; caution: string }
  sources: GrammarSource[]
  l1_notes: { form: string; reviewed: boolean; common_mistakes: string[]; explain_tip: string }[]
  grounded: boolean
}

export interface GrammarSources {
  forms: GrammarForm[]
  out_of_level: { form: string; level: number }[]
  ungrounded_forms: string[]
  removed_points: string[]
  ai_note: string
}

/** ai-server POST /grammar-qa 응답. Spring이 points는 token으로, 나머지는 sources로 나눠 보낸다 */
export interface GrammarQaResult extends GrammarSources {
  points: string[]
  grounded: boolean
}

// AI 추적 (LangSmith 실행 기록, ai-server /traces 그대로, snake_case, 기술 ADR-0028)
export type TraceStatus = 'success' | 'error' | 'running'
export type TraceRunType = 'chain' | 'llm' | 'retriever' | 'tool' | 'prompt' | 'parser' | 'embedding'

export interface TraceRow {
  id: string
  trace_id: string
  name: string
  label: string
  start_time: string | null
  latency_ms: number | null
  status: TraceStatus
  error: string | null
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  total_cost: number | null
  thread_id: string | null
  url: string | null
}

export interface TraceSummaryStats {
  count: number
  errors: number
  avg_latency_ms: number | null
  total_tokens: number
  total_cost: number | null
}

export type TraceList =
  | { enabled: false; project: string }
  | { enabled: true; project: string; summary: TraceSummaryStats; runs: TraceRow[] }

export interface TraceNode {
  id: string
  name: string
  label: string
  run_type: TraceRunType
  start_offset_ms: number
  latency_ms: number | null
  status: TraceStatus
  error: string | null
  total_tokens: number
  model: string | null
  inputs: string | null
  outputs: string | null
  children: TraceNode[]
}

export type TraceDetail =
  | { enabled: false; project: string }
  | (TraceRow & { enabled: true; project: string; total_latency_ms: number | null; root: TraceNode })

/** 원본 PDF 열기 결과 (기술 ADR-0030). page = 실제로 연 PDF 쪽 (null이면 첫 쪽부터 열림) */
export interface MaterialOpenResult {
  opened: boolean
  page?: number | null
  message?: string
}

// 교재 항목 ID(u03-v01)를 화면에서 이름("노래")으로 보여 주기 위한 정보 (기술 ADR-0029)
export interface TextbookItem {
  kind: 'vocab' | 'grammar' | 'dialogue' | 'reading' | 'exercise'
  label: string
  meaning: string | null
  unit_no: number
}

/** 교재 시리즈 ID → 화면 이름 (단원 시트, 기술 ADR-0032) */
export const BOOK_NAMES: Record<string, string> = { ko1: '한국어 1', ko2: '한국어 2' }
export const bookName = (id: string | undefined | null) => BOOK_NAMES[id ?? 'ko1'] ?? id ?? ''

/** 단원 시트 목록 (기술 ADR-0032). 수업 준비에서 교재·과를 고른다 */
export interface CurriculumUnit {
  unit_no: number
  title: string
  status: 'draft' | 'reviewed'
}
export interface CurriculumBook {
  id: string
  title: string
  units: CurriculumUnit[]
}
