import { ApiError } from './http'

export type SseHandler = (event: string, data: any) => void

/**
 * POST 요청으로 SSE를 받는다. EventSource는 GET만 되므로 fetch + 스트림으로 직접 읽는다 (ADR-0003).
 * Spring은 "event:이름\ndata:JSON\n\n" 모양으로 보낸다.
 * 끝까지 받으면 resolve. 서버가 error 이벤트를 보내면 handler로 전달만 하고 스트림은 계속 읽는다.
 */
export async function streamSse(path: string, body: unknown, onEvent: SseHandler, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body ?? {}),
    signal,
  })
  if (!res.ok || !res.body) {
    let err = { code: 'HTTP_' + res.status, message: res.statusText, retryable: res.status >= 500 }
    try {
      err = await res.json()
    } catch {
      // 기본값 사용
    }
    throw new ApiError(res.status, err)
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value.replace(/\r\n/g, '\n')
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      dispatch(buffer.slice(0, sep), onEvent)
      buffer = buffer.slice(sep + 2)
    }
  }
  if (buffer.trim()) dispatch(buffer, onEvent)
}

function dispatch(block: string, onEvent: SseHandler) {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
  }
  if (!data.length) return
  const raw = data.join('\n')
  let parsed: unknown = raw
  try {
    parsed = JSON.parse(raw)
  } catch {
    // JSON이 아니면 글 그대로
  }
  onEvent(event, parsed)
}
