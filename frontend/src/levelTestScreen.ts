// 레벨테스트 학생 화면 (기획 ADR-0021, 기술 ADR-0019).
// 선생님 화면(/level-test)과 학생 화면(/level-test/screen)은 같은 브라우저의 두 창이다. 선생님이 학생 화면 창만 화상수업에서 공유한다.
// 그래서 서버를 거치지 않고 BroadcastChannel로 "지금 보여 줄 문항"만 보낸다. 예시 답·확인할 점·표준 ID는 보내지 않는다.

export type ScreenLang = 'ko' | 'en' | 'ja'

export interface ScreenItem {
  kind: 'hangul' | 'grammar' | 'vocab'
  text: string // 학생에게 보여 줄 글 (단어 또는 질문)
  level: number | null // null = 한글 읽기
  index: number // 그 묶음 안에서 몇 번째 (1부터)
  total: number
}

export type ScreenMessage =
  | { type: 'hello' } // 학생 화면이 열렸다 → 선생님 화면이 지금 상태를 다시 보낸다
  | { type: 'show'; lang: ScreenLang; item: ScreenItem | null } // null = 시작 전 대기 화면
  | { type: 'done'; lang: ScreenLang } // 결과를 저장했다

export const SCREEN_CHANNEL = 'level-test-screen'
export const openScreenChannel = () => new BroadcastChannel(SCREEN_CHANNEL)

export const SCREEN_LANG_NAMES: Record<ScreenLang, string> = { ko: '한국어만', en: 'English', ja: '日本語' }

/** 학생에게 보이는 안내 문구. 한국어 문장 아래에 학생 언어로 한 줄 더 쓴다 (ko면 한국어만) */
export const SCREEN_TEXT = {
  ko: {
    title: '한국어 레벨테스트',
    waiting: '곧 시작해요',
    done: '수고했어요! 감사합니다.',
    hangul: '소리 내어 읽어 보세요.',
    grammar: '한국어로 대답해 보세요.',
    vocab: '무슨 뜻이에요? 이 단어로 문장을 만들어 보세요.',
    partHangul: '한글 읽기',
    part: (n: number) => `${n}단계`,
  },
  en: {
    title: 'Korean level check',
    waiting: 'We will start soon.',
    done: 'Great job! Thank you.',
    hangul: 'Read it aloud.',
    grammar: 'Answer in Korean.',
    vocab: 'What does it mean? Try making a sentence with it.',
    partHangul: 'Reading Hangul',
    part: (n: number) => `Part ${n}`,
  },
  ja: {
    title: '韓国語レベルチェック',
    waiting: 'まもなく始まります。',
    done: 'お疲れさまでした！ありがとうございました。',
    hangul: '声に出して読んでみてください。',
    grammar: '韓国語で答えてみてください。',
    vocab: 'どういう意味ですか？この単語で文を作ってみてください。',
    partHangul: 'ハングルを読む',
    part: (n: number) => `パート${n}`,
  },
} satisfies Record<ScreenLang, unknown>
