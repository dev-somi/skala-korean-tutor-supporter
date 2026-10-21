# ADR-0012: 개발 중에는 로컬 Ollama(qwen3:8b)를 쓰고, 데모·평가만 Anthropic을 쓴다
- 상태: Accepted (2026-10-20) — "데모·평가만 Anthropic" 항목만 Superseded by ADR-0020 (2026-10-20)
- 관련 모듈: `ai-server/app/agent/lesson_prep/llm.py`, `backend` (`ChatClientConfig`, `application.yml`), `.env`, `scripts/setup_ollama.sh`

## 배경 (Context)
개발하면서 그래프를 여러 번 돌리다 보니 API 토큰을 너무 많이 썼다. 수업 준비 한 번이 자동 검토 재시도까지 LLM을 여러 번 부른다.
[ADR-0007](0007-llm-provider-tiering.md)에서는 로컬 모델을 "설치·성능 확인이 추가된다"는 이유로 기각했지만, 이 맥북(16GB)에는 이미 Ollama와 `qwen3:8b`가 있고, 수업 참고 프로젝트(`all_total_vue_student`)도 같은 방식으로 로컬 모델을 쓴다.

## 결정 (Decision)
- `.env`의 `LLM_PROVIDER`(Spring)와 `LLM_MODEL_FAST` / `LLM_MODEL_QUALITY`(두 서비스)만 바꿔서 Anthropic과 Ollama를 오간다. 코드 분기는 두 곳뿐이다.
  - ai-server: 모델 문자열이 `ollama:`로 시작하면 `init_chat_model`에 `num_ctx`, `reasoning=False`, `temperature=0`을 넘긴다 (`langchain-ollama`).
  - backend: `spring.ai.model.chat=${LLM_PROVIDER}`로 ChatModel을 고르고, `OllamaChatModel`이면 `OllamaChatOptions`(numCtx, 생각 끄기)를 쓴다.
- 두 티어 모두 `qwen3:8b` 하나를 쓴다. 16GB에서 모델 두 개를 번갈아 올리면 느려지고, 0.6b 같은 작은 모델은 이 프로젝트의 중첩 JSON 출력을 못 맞춘다.
- `num_ctx`는 16384로 올린다. Ollama 기본값 4096은 교재 목록이 든 프롬프트를 잘라 버린다.
- qwen3의 생각(thinking) 출력은 끈다. 구조화 출력에서 시간만 늘린다.
- 데모 녹화와 평가 수치(PRD 10장) 보고는 Anthropic으로 한다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 계속 Anthropic만 | 지금 그대로 | 품질이 가장 좋다 | 개발 중 토큰 비용이 계속 든다 |
| 개발 중에도 Haiku만 | 두 티어를 Haiku로 | 코드 변경이 없다 | 비용은 줄지만 0이 아니고, 결국 API 키가 필요하다 |
| fast는 qwen3:0.6b, quality는 qwen3:8b | 참고 프로젝트 기본값 | 라우팅이 빠르다 | 0.6b는 한국어 구조화 추출이 불안정하고, 모델 두 개를 메모리에 올려야 한다 |
| 가짜 LLM만 | 테스트처럼 | 비용 0, 결정적 | 프롬프트·출력 품질을 확인할 수 없다 (테스트에는 이미 쓰고 있음) |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 개발 중 API 비용이 0이다. 2026-10-20 확인: 학생 등록 약 13초, 채팅 라우팅 + 답변 약 10초, 수업 후 기록(추출 + 메시지 + Validator) 케이스당 약 35초.
- 대가: 품질이 떨어진다. 수업 후 기록 추출 정확도는 3개 케이스에서 0.922(Sonnet 16개 첫 실행은 0.969)였고, 학생 등록에서 이름을 놓치거나 채팅 답변에 "교재 항목 ID: null" 같은 내부 값이 섞여 나왔다. 로컬 결과로 프롬프트를 고치면 Claude에서는 다르게 동작할 수 있다.
- 대가: 수업 준비는 긴 출력(설명·대본)이 많아 Anthropic보다 훨씬 오래 걸린다.
- backend에 `spring-ai-starter-model-ollama` 의존성이 하나 늘었다.

## 재검토 조건
- 로컬 결과와 Claude 결과가 자주 달라서 프롬프트 작업이 두 번이 될 때 → 프롬프트 작업만 Haiku로 한다
- 수업 준비가 너무 느려서 개발이 막힐 때 → 수업 준비만 Anthropic, 나머지는 Ollama로 섞는다 (티어별 환경변수가 이미 나뉘어 있다)
- 메모리가 더 큰 머신을 쓰게 되면 → `qwen3:14b` 이상으로 올린다
