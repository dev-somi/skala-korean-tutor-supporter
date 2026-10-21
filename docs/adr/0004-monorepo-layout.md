# ADR-0004: `ai-service-test` 모노레포 구조
- 상태: Accepted (2026-10-19)
- 관련 모듈: 저장소 전체

## 배경 (Context)
서비스가 세 개(Vue, Spring, FastAPI)가 됐다. 기존 수업 준비 에이전트는 `korean-ppt-ai-agent` 저장소에 있고, PRD와 참고노트는 `ai-service-test`에 있다.
혼자 4일 안에 만들고, 한 번에 제출해야 한다.

## 결정 (Decision)
`ai-service-test/` 하나에 모은다.
```
ai-service-test/
├─ frontend/    Vue
├─ backend/     Spring Boot
├─ ai-server/   FastAPI + LangGraph (korean-ppt-ai-agent 코드를 복사해 옮김)
├─ shared/      constraints.json (공통 상수)
├─ docs/adr/
└─ docker-compose.yml
```
`korean-ppt-ai-agent`는 수정하지 않고 이전 과제 제출본으로 남겨 둔다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| `korean-ppt-ai-agent` 확장 | 기존 저장소에 frontend/, backend/ 추가 | 코드 이동이 없고 git 이력이 이어진다 | 이전 과제 제출본과 섞이고, 루트에 PDF·노트북·제출 폴더가 많아 구조가 지저분하다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 한 저장소로 제출·실행한다. 공통 상수(`shared/`)를 세 서비스가 같이 읽는다.
- 대가: 에이전트 코드의 git 이력이 끊긴다 → 첫 커밋 메시지에 원본 저장소를 적어 둔다.
- 교재 저작권: 저장소를 공개할 때 `ai-server/data/textbook/`과 교재 PDF는 제외한다(PRD 12장).

## 재검토 조건
- 서비스별 배포 주기가 달라지거나 다른 사람과 협업하게 될 때
