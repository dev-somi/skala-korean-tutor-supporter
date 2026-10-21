# CLAUDE.md

요구사항은 [PRD.md](PRD.md), 실행 방법은 [README.md](README.md).

## 결정이 바뀌면 ADR을 쓴다

코드를 고치거나 기획을 바꾸다가 **설계·기획 결정이 생기거나 바뀌면** 같은 작업 안에서 ADR을 남긴다. 템플릿은 [AI_Capstone_개인프로젝트_참고노트.md](docs/reference/AI_Capstone_개인프로젝트_참고노트.md) 1장.

| 무엇이 바뀌었나 | 쓸 곳 | 예 |
|---|---|---|
| 기획 (범위, 기능 우선순위, 대상 사용자, 입력 방식, 성공 지표) | [docs/planning-adr/](docs/planning-adr/README.md) | 수업 기록을 녹음 STT로도 받는다 |
| 기술 설계 (구조, 라이브러리, API, 데이터 모델, 그래프 흐름, 모델 선택) | [docs/adr/](docs/adr/README.md) | 녹취록 입력 단계를 post_lesson 앞에 둔다 |

- 새 ADR은 그 폴더의 다음 번호로 만들고, 상태에 날짜를 적는다: `상태: Accepted (YYYY-MM-DD)`.
- 그 폴더의 `README.md` 목록 표에 한 줄 추가한다.
- 기존 결정을 뒤집으면 기존 ADR은 지우지 않고 상태를 `Superseded by ADR-000N (YYYY-MM-DD)`로 바꾸고, 새 ADR에서 기존 ADR을 링크한다.
- 결정 때문에 PRD.md나 README.md 내용이 틀려지면 같이 고친다.
- 대안이 없던 변경(단순 버그 수정, 이름 바꾸기, 결정이 바뀌지 않는 리팩터링)은 ADR을 쓰지 않는다. 애매하면 사용자에게 물어본다.

## 막혔다가 풀리면 트러블슈팅 기록을 쓴다

작업하다가 **해 봤는데 안 됐고, 원인을 찾아서 고친 일**이 생기면 같은 작업 안에서 [docs/troubleshooting/](docs/troubleshooting/README.md)에 기록한다. 결정이 아니라 "무엇이 왜 안 됐고 어떻게 풀었나"를 남기는 곳이다.

- 쓰는 경우: 에러·오작동이 나서 원인을 따로 찾아야 했던 일, 처음 시도한 방법이 안 통해서 다른 방법으로 바꾼 일 (예: Ollama 응답이 JSON이 아니어서 파싱 실패 → `format=json` + 재시도로 수정)
- 안 쓰는 경우: 오타, 바로 보이는 단순 실수처럼 원인을 찾을 필요가 없던 수정
- 파일은 `docs/troubleshooting/000N-짧은-제목.md`로 다음 번호를 쓰고, 폴더 `README.md` 목록 표에 한 줄 추가한다.
- 고치는 과정에서 설계·기획 결정이 바뀌었으면 ADR도 쓰고, 두 문서가 서로 링크한다.

템플릿:

```markdown
# TS-000N: <무엇이 안 됐나, 한 줄>
- 날짜: YYYY-MM-DD
- 관련 모듈:
- 관련 ADR: (있으면)

## 증상
무엇을 하려고 했고, 실제로 어떻게 됐나. 에러 메시지·로그는 그대로 붙인다.

## 원인
왜 그랬나. 처음에 짐작했다가 틀린 원인이 있었으면 같이 적는다.

## 시도한 것
| 시도 | 결과 |
|---|---|

## 해결
최종적으로 무엇을 어떻게 바꿨나 (파일·설정·명령).

## 배운 점 / 다음에 주의할 것
```

## 개발 서버와 확인

사용자는 `bash scripts/dev.sh` 하나로 Postgres + ai-server + backend + frontend를 띄워 둔다 ([기술 ADR-0026](docs/adr/0026-single-dev-script.md)). 저장하면 자동으로 반영된다 (uvicorn `--reload`, Vite HMR, Spring devtools).

- 코드를 고친 뒤 서버를 직접 다시 띄우지 않는다. 반영됐는지는 `.dev-logs/{ai,api,build,web}.log`를 읽어 확인한다 (에러, 재시작 줄).
- `.dev-logs/`가 없거나 오래됐으면(서버가 안 떠 있으면) 사용자에게 `bash scripts/dev.sh` 실행을 부탁한다. Claude가 백그라운드로 띄우지 않는다 (포트가 겹친다).
- 의존성(`ai-server/pyproject.toml`, `frontend/package.json`, `backend/build.gradle`)이나 `.env`를 바꾸면 자동 반영이 안 된다. 사용자에게 dev.sh를 다시 실행해 달라고 말한다.
- 새 인프라(DB, 큐 등)가 필요하면 `docker-compose.yml`에 서비스를 추가하고 dev.sh의 Postgres 단계 옆에 함께 띄운다. 앱 서비스(ai-server, backend, frontend)는 컨테이너로 옮기지 않는다 (ADR-0008, 0026).
- 실행 방법이 바뀌면 README.md "실행"과 dev.sh 머리 주석을 같이 고친다.
