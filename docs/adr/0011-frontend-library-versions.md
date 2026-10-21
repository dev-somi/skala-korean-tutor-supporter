# ADR-0011: 프론트 라이브러리는 이전 메이저 버전으로 고정
- 상태: Accepted (2026-10-19)
- 관련 모듈: `frontend/package.json`

## 배경 (Context)
2026-10 기준 최신 버전은 PrimeVue 5, Pinia 4, vue-router 5, TypeScript 7이다. 마감까지 이틀이고, 새 메이저의 API 변경을 확인할 시간이 없다.

## 결정 (Decision)
메이저를 하나 낮춰 정확한 버전으로 고정한다: PrimeVue 4.5.5(+ @primeuix/themes 1.2.5), Pinia 3.0.4, vue-router 4.6.4, Vite 7.3.7, TypeScript 5.9.3. Vue 3.5와 Tailwind 4는 최신.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 모두 최신 | create-vite 기본값 | 오래 쓸 수 있다 | 문서·예제가 적고 API 변경을 확인할 시간이 없다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 익숙한 API로 빠르게 만들고, 타입 검사·빌드가 한 번에 통과했다.
- 대가: 나중에 메이저 업그레이드가 필요하다.

## 재검토 조건
- 제출 후 계속 쓰기로 하면 → PrimeVue 5 마이그레이션 가이드를 보고 올린다
