import { ApiError } from './api/http'

export function formatDate(value: string | null | undefined): string {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', weekday: 'short' })
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export interface UiError {
  message: string
  retryable: boolean
}

export function toUiError(e: unknown): UiError {
  if (e instanceof ApiError) return { message: e.message, retryable: e.retryable }
  if (e instanceof Error) return { message: e.message, retryable: true }
  return { message: String(e), retryable: true }
}

/** 줄바꿈으로 나눈 글 ↔ 목록 (폼의 목표·관심사 입력용) */
export const linesToList = (text: string) => text.split('\n').map(s => s.trim()).filter(Boolean)
export const listToLines = (list: string[] | null | undefined) => (list ?? []).join('\n')
