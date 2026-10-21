# ADR-0003: 프론트엔드 스택 — Vue 3 + Vite + TypeScript + Pinia + PrimeVue + Tailwind
- 상태: Accepted (2026-10-19) — PRD 13장 열린 질문 1을 닫는다
- 관련 모듈: `frontend/`

## 배경 (Context)
대시보드(학생 카드, 할 일), 검토 화면(범주별 승인·수정·피드백, 항목별 승인), 채팅 패널(SSE)이 필요하다.
PRD는 React + Vite와 Streamlit을 비교했지만, 프론트는 Vue로 하기로 했다. 남은 문제는 Vue 안에서 어떤 도구를 쓸지다.

## 결정 (Decision)
Vue 3 + Vite + **TypeScript** + Pinia + Vue Router + **PrimeVue**(컴포넌트) + **Tailwind**(레이아웃·간격).

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| Vue3 + TS + Pinia + Vuetify | Material 컴포넌트 | 카드·폼·타임라인이 다 있다 | Material 스타일 때문에 Tailwind와 섞어 쓰기 불편하다 |
| Vue3 + JS + Pinia + Element Plus | JavaScript | 타입 설정이 필요 없다 | 백엔드 DTO·SSE 이벤트 모양을 타입으로 확인할 수 없다 |
| Vue3 + TS + Pinia + Tailwind만 | UI 라이브러리 없음 | 자유도가 높다 | 다이얼로그·테이블·스텝을 직접 만들 시간이 없다 |
| React + Vite (PRD 원안) | 참고노트 구조 | Vercel AI SDK `useChat` | 프론트를 Vue로 하기로 함 |
| Streamlit (PRD 원안) | Python만으로 UI | 가장 빠르다 | Spring 백엔드와 맞지 않고, 실사용 화면으로 쓰기 어렵다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: PrimeVue의 DataTable, Dialog, Stepper, Timeline으로 검토·대시보드 화면을 빨리 만든다. TS로 SSE 이벤트 타입을 확인한다.
- 대가: PrimeVue 테마와 Tailwind 클래스가 겹칠 수 있다 → PrimeVue는 unstyled/preset 중 하나로 정하고 Tailwind는 레이아웃에만 쓴다.
- POST 요청으로 SSE를 받아야 해서 `EventSource` 대신 `fetch` + 스트림 파서를 쓴다.

## 재검토 조건
- 10/21(수) 오전까지 검토 화면이 동작하지 않으면 UI 라이브러리 사용을 줄이고 기능 우선으로 단순화한다
