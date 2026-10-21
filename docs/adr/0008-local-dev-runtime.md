# ADR-0008: 개발·데모 실행 방식 — Postgres만 Docker, 나머지는 로컬
- 상태: Accepted (2026-10-19)
- 관련 모듈: `docker-compose.yml`, README 실행 절차

## 배경 (Context)
서비스 3개 + DB 1개를 개발 중에 자주 껐다 켜야 하고, 데모 영상도 찍어야 한다.
render_check는 LibreOffice(PDF 변환)를 쓰는데, 컨테이너에 넣으면 이미지가 커지고 글꼴 설정이 필요하다.

## 결정 (Decision)
- `docker compose up -d`로 **Postgres만** 띄운다.
- Vue: `npm run dev` (5173) / Spring: `./gradlew bootRun` (8080) / FastAPI: `uv run uvicorn app.main:app --reload` (8000).
- `--reload`는 개발에서만 쓴다(참고노트 6장).

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 전부 docker compose | 4개 서비스 모두 컨테이너 | 제출·재현이 쉽다 | LibreOffice·글꼴 이미지 세팅에 시간이 들고, 개발 중 디버깅·핫리로드가 불편하다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: IDE 디버거와 핫리로드를 그대로 쓴다. 세팅 시간이 거의 없다.
- 대가: 다른 사람이 실행하려면 Java 21, Node, uv, LibreOffice(선택)를 설치해야 한다 → README에 버전과 순서를 적는다.

## 재검토 조건
- 제출·재현용 패키징이 필요할 때 → 10/22(목)에 시간이 남으면 나머지 서비스의 Dockerfile을 추가한다
