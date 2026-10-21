# ADR-0026: 개발 실행은 스크립트 하나로 — 세 서비스를 한 터미널에, 저장하면 자동 반영
- 상태: Accepted (2026-10-21)
- 관련 모듈: `scripts/dev.sh`, `backend/build.gradle` (devtools), `CLAUDE.md`
- 관련 ADR: [ADR-0008](0008-local-dev-runtime.md) (로컬 실행 유지)

## 배경 (Context)
- ADR-0008대로 Postgres만 컨테이너로 띄우고 세 서비스는 로컬에서 돈다. 그런데 터미널 3개를 따로 띄워야 해서 귀찮다.
- Spring은 `bootRun`만으로는 코드를 고쳐도 다시 뜨지 않아서 매번 껐다 켜야 했다.
- Claude Code가 코드를 고친 뒤 반영됐는지 확인할 방법이 없었다 (로그가 사용자 터미널에만 있다).

## 결정 (Decision)
1. `scripts/dev.sh` 하나가 Docker·포트·Ollama를 확인하고, Postgres(`docker compose up --wait`) → 의존성 동기화 → ai-server·backend·frontend를 띄운다. 로그는 `[ai] [api] [build] [web]` 접두어로 한 터미널에 합쳐 보이고, Ctrl+C 한 번에 모두 끈다.
2. 자동 반영: ai-server `uvicorn --reload`, frontend Vite HMR, backend는 `gradlew -t classes`(바뀐 Java 계속 컴파일) + `spring-boot-devtools`(클래스가 바뀌면 재시작). devtools는 `developmentOnly`라 jar에는 들어가지 않는다.
3. 로그를 `.dev-logs/<이름>.log`에도 남긴다 (git 제외). Claude는 코드를 고친 뒤 이 파일로 반영·에러를 확인하고, 서버를 직접 띄우지 않는다 (CLAUDE.md).

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 전부 docker compose + `compose watch` | 세 서비스를 컨테이너로, 변경 감지 동기화·재빌드 | 제출·재현이 쉽다 | Dockerfile 3개를 새로 써야 하고 Spring 재빌드가 느리다. Ollama·RAG 색인(macOS OCR 결과)을 호스트에서 연결해야 한다. 마감 하루 전 |
| tmux / overmind 같은 프로세스 관리자 | Procfile로 여러 프로세스 | 기능이 많다 | 도구를 하나 더 설치해야 한다. bash 스크립트로 충분하다 |
| 그대로 (터미널 3개) | ADR-0008 그대로 | 바꿀 게 없다 | 귀찮고, Spring 재시작을 잊고, Claude가 로그를 못 본다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 명령 하나로 개발 환경이 뜨고, 저장만 하면 세 서비스 모두 반영된다.
- 좋은 점: Claude가 `.dev-logs/`로 반영 여부와 에러를 직접 확인한다.
- 대가: backend는 bootRun과 연속 컴파일 두 Gradle 프로세스가 돈다. bootRun이 뜬 뒤에 연속 컴파일을 시작해 build/ 폴더 충돌을 피한다.
- 대가: 의존성이나 `.env`를 바꾸면 스크립트를 다시 실행해야 한다.
- 대가: macOS·bash 기준이다 (`lsof`, `curl`).

## 재검토 조건
- 다른 사람이 실행해야 하거나 배포가 필요해지면 → 대안 1(전부 compose)로 옮긴다
