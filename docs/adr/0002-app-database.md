# ADR-0002: 앱 데이터 저장소로 PostgreSQL 사용
- 상태: Accepted (2026-10-19)
- 관련 모듈: `backend/` (Spring Data JPA, Flyway), `docker-compose.yml`

## 배경 (Context)
학생, 약점, 수업, 수업 후 기록, TimeLog, Baseline(PRD 7장)을 저장할 DB가 필요하다.
PRD 원안은 SQLite였지만 그때는 Python 백엔드가 전제였다. 이제 DB를 다루는 쪽은 Spring(JPA)이다(ADR-0005).
LangGraph checkpointer는 이것과 별개로 FastAPI 쪽에 둔다.

## 결정 (Decision)
- 앱 데이터: **PostgreSQL 16**, docker compose로 실행. 스키마는 Flyway로 관리한다.
- 구성안·브리핑·추출 결과처럼 모양이 자주 바뀌는 값은 `jsonb` 칼럼에 넣는다.
- LangGraph checkpointer: FastAPI 쪽 **SQLite 파일**(`AsyncSqliteSaver`)을 그대로 쓴다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| SQLite | PRD 원안. 파일 하나 | 설치 없음 | JPA/Hibernate와 쓰려면 커뮤니티 dialect 설정이 필요하고 `jsonb` 같은 타입이 없다 |
| H2 (파일 모드) | Spring 내장 DB | 설정이 가장 간단 | 외부 도구로 데이터를 보기 불편하고, 데모용 이상으로 키우기 어렵다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: JPA와 궁합이 좋고 `jsonb`로 스키마 변경 부담이 줄어든다. 나중에 checkpointer도 Postgres로 옮길 수 있다.
- 대가: Docker가 떠 있어야 한다. 저장소가 두 개(Postgres + SQLite 파일)가 된다 → 수업 행에 `prep_thread_id`를 저장해 둘을 잇는다.

## 재검토 조건
- 여러 인스턴스로 배포해 checkpointer를 공유해야 할 때 → checkpointer도 Postgres(`AsyncPostgresSaver`)로 옮긴다 (참고노트 2장 #14)
