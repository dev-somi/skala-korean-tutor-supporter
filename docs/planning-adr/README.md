# ADR 목록

PRD(`../PRD.md`)를 쓰기 전에 기획 확정 질문을 하고 답을 받았다. 그 답 중에서 대안이 있었던 결정만 ADR로 남긴다.
템플릿은 [참고노트](../reference/AI_Capstone_개인프로젝트_참고노트.md) 1장을 따른다.

- 결정일: 2026-10-19
- 결정자: 박소미 (단독 프로젝트)

## 공통 배경 (질문 1, 3)

- 캡스톤 과제로 제출하지만, **실제 선생님이 쓸 수 있는 서비스**를 목표로 한다.
- 혼자 개발하고, 마감은 **2026-10-22(목)** 이다.
- 내가 직접 Preply/AmazingTalker 선생님으로 일하면서 이 서비스를 쓴다. 수업할 학생도 몇 명 있다. 그래서 페르소나와 pain point는 내 경험(예전에 일본인에게 한국어를 가르친 경험)을 근거로 쓴다.

## 목록

| # | 제목 | 상태 | 질문 |
|---|---|---|---|
| [0001](0001-extend-existing-agent.md) | 기존 수업 자료 생성 에이전트를 확장한다 | Accepted | Q2 |
| [0002](0002-scope-learning-management-only.md) | 범위를 학습 관리로 한정한다 (예약·결제·수익 모델 제외) | Accepted | Q4, Q5, Q14 |
| [0003](0003-lesson-record-input.md) | 수업 기록은 선생님 메모로 받는다 (녹음 분석은 나중에) | Accepted, P2 녹음 파일 항목만 Superseded by 0026 (2026-10-21) | Q6 |
| [0004](0004-student-registration.md) | 학생 등록은 정해진 엔티티 + 수동 입력/자연어 AI 채움/자유 메모 | Accepted | Q7 |
| [0005](0005-teacher-only.md) | 선생님 전용 서비스로 만든다 | Accepted | Q8 |
| [0006](0006-sejong-textbook-only.md) | 교재는 세종학당 한국어 1로 고정한다 | Superseded by 0013 | Q9 |
| [0007](0007-explanation-languages.md) | 설명 언어는 일본어·영어만 지원한다 | Accepted | Q10 |
| [0008](0008-dashboard-plus-chat.md) | UI는 대시보드 GUI + 채팅 | Accepted | Q11 |
| [0009](0009-hitl-on-all-writes.md) | AI는 DB에 직접 쓰지 않는다 (모든 쓰기에 HITL) | Accepted | Q12 |
| [0010](0010-success-metric-prep-time.md) | 성공 지표는 수업 준비 시간, 서비스가 직접 측정 | Superseded by 0020 (2026-10-20) | Q13 |
| [0011](0011-virtual-data-only.md) | MVP는 가상 데이터만 쓴다 | Accepted | Q15 |
| [0012](0012-frontend-stack.md) | 프론트엔드 스택 | Proposed | PRD 열린 질문 1 |
| [0013](0013-sejong-public-materials.md) | 교재 범위를 세종학당 공개 자료(교재·지침서·핸드북)로 넓힌다 | Accepted (2026-10-20), 기준 교재 항목만 Superseded by 0016 | 기획 재검토 |
| [0014](0014-personalization-scope.md) | 수업 준비의 핵심은 맞춤 설명, 개인화 축은 모국어·수준·관심사 | Superseded by 0016, 0017 (2026-10-20) | 기획 재검토 |
| [0015](0015-no-ppt-fixed-lesson-frame.md) | PPT는 만들지 않고, 고정된 7단계 수업 틀에 내용만 채운다 | Accepted (2026-10-20) | 기획 재검토 |
| [0016](0016-persona-anchor-textbook-standard-levels.md) | 페르소나가 중심 교재를 정하고, 국립국어원 표준 등급 목록을 공통 기준으로 둔다 | Accepted (2026-10-20), 체계적 학습 교재 줄만 Superseded by 0022 | 기획 재검토 |
| [0017](0017-examples-from-materials-not-generated.md) | 예문은 만들지 않고 세종학당 자료에서 찾고, 학생 등급을 넘는 예문은 거른다 | Accepted (2026-10-20) | 기획 재검토 |
| [0018](0018-level-from-trial-test-persona-by-teacher.md) | 현재 수준은 체험수업 레벨테스트로 정한 표준 등급을 필수로, 학습 목적은 선생님이 고른다 | Accepted (2026-10-20), 레벨테스트 결과 처리만 Superseded by 0021 | 기획 재검토 |
| [0019](0019-progress-report-for-retention.md) | 학습자별 진도·향상 리포트 — 코드 계산, 학생에게는 개수와 늘어난 양만 | Accepted (2026-10-20) | 선생님 페인포인트 재정리 |
| [0020](0020-primary-metric-draft-quality.md) | 주 지표를 "AI 초안을 그대로 승인한 비율"로, 준비 시간은 보조로 | Accepted (2026-10-20) | 선생님 페인포인트 재정리 |
| [0021](0021-student-screen-level-test-saved-result.md) | 레벨테스트에 화면 공유용 학생 화면, 결과는 저장 후 선생님 확인으로 학생 카드에 반영 | Accepted (2026-10-20) | 체험수업 사용 |
| [0022](0022-structured-persona-uses-sejong-korean-1-6.md) | "체계적 학습 · TOPIK 준비"의 중심 교재를 「세종학당 한국어 1~6」으로 | Accepted (2026-10-20) | 온라인 세종학당 커리큘럼 확인 |
| [0023](0023-culture-point-from-sejong-materials.md) | 매 수업에 문화 포인트 — 진도는 교재, 문화는 세종학당 자료에서 RAG로 골라 정리, 비교는 질문으로 | Accepted (2026-10-20) | 문화 필수 |
| [0024](0024-grammar-qa-chat-p0.md) | 교재 근거 문법 질문 챗봇을 P0로 — "이거랑 이거 뭐가 달라?"에 교재로 답한다, 멀티 에이전트는 쓰지 않는다 | Accepted (2026-10-21) | 발표 스토리 재정리 |
| [0025](0025-material-tiers.md) | 색인할 세종학당 자료를 3순위로 — 교사용 설명 먼저, 본책 다음, 연습 자료는 나중, 근로자용·EPS 제외 | Accepted (2026-10-21) | 지도교수 의견 (전부 텍스트화) |
| [0026](0026-transcript-text-upload.md) | 수업 후 기록에 녹취록 텍스트 파일(.txt)도 받는다 — STT는 서비스 밖에서 | Accepted (2026-10-21) | 수업 녹음 활용 |
| [0027](0027-open-source-pdf.md) | 출처 옆 "원문"을 누르면 선생님 컴퓨터의 원본 PDF가 그 쪽으로 열린다 | Accepted (2026-10-21) | 원문 확인이 번거롭다 |

## 아직 정하지 않은 것 (PRD 13장)

- 음성 메모를 P0로 올릴지 → 0003의 재검토 조건
- 숙제 채점 기능을 넣을지
- 수업 시간 기본값 (50분 고정 vs 학생별 설정)
- 캡스톤 제출 형식 (데모 영상, 발표 자료, 코드 저장소)
