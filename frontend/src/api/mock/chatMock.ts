// 채팅 SSE mock (기술 ADR-0027). 개발 중 주소에 ?mock 을 붙이면 backend·ai-server 없이 이 스트림을 쓴다.
// Spring ChatService 와 같은 순서로 이벤트를 보낸다: routing_decided → sources → token → done.
import type { SseHandler } from '../sse'
import { pickScenario } from './grammarFixtures'

const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    const t = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(t)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })

const jitter = (min: number, max: number) => min + Math.random() * (max - min)

export async function mockStream(message: string, onEvent: SseHandler, signal?: AbortSignal): Promise<void> {
  const s = pickScenario(message)
  await wait(jitter(400, 800), signal) // 라우팅 (저가 모델)
  onEvent('routing_decided', s.routing)

  if (s.error) {
    await wait(1200, signal)
    onEvent('error', s.error)
    return
  }

  let text = s.text ?? ''
  if (s.grammar) {
    await wait(jitter(1500, 3000), signal) // RAG 검색 + 요점 생성
    const { points, grounded: _grounded, ...sources } = s.grammar
    onEvent('sources', sources)
    text = points.map(p => '• ' + p).join('\n')
  }

  // 실제 grammar_qa 는 글을 한 번에 보내지만, 일반 질문 스트리밍처럼 보이게 조각낸다
  for (const chunk of text.match(/.{1,8}/gs) ?? []) {
    await wait(30, signal)
    onEvent('token', { text: chunk })
  }
  onEvent('done', {})
}
