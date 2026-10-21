# ADR-0007: LLM 공급사 Anthropic + 모델 티어링(Haiku / Sonnet)
- 상태: Accepted (2026-10-19)
- 관련 모듈: `backend` (Spring AI `ChatClient` 빈), `ai-server/app/llm.py`

## 배경 (Context)
라우팅·검증처럼 단순한 판단과, 설명·대본·브리핑·피드백 메시지처럼 품질이 체감되는 생성이 섞여 있다.
같은 모델을 쓰면 단순 판단에 비용을 낭비한다(참고노트 5-1). 기존 에이전트는 Anthropic(`langchain-anthropic`)을 쓴다.

## 결정 (Decision)
- 공급사: **Anthropic**. Spring은 `spring-ai-starter-model-anthropic`, FastAPI는 `langchain-anthropic`.
- 저가 티어 `claude-haiku-5-5`: 채팅 라우팅, 학생 정보 추출, Validator, 조회 답변.
- 고품질 티어 `claude-sonnet-5-5`: 구성안·개인화 설명·대본·선생님 브리핑·피드백 메시지.
- 모델명은 `.env`의 `LLM_MODEL_FAST`, `LLM_MODEL_QUALITY`로 바꾼다. 두 서비스가 같은 키 이름을 쓴다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| OpenAI | 기존 `ai-spring` 연습 프로젝트와 같음 | Spring AI 예제가 많다 | 기존 Python 그래프와 프롬프트를 Anthropic 기준으로 맞춰 두어서 다시 맞추는 시간이 든다 |
| Ollama 로컬 + 클라우드 혼합 | 라우터는 로컬 모델 | 라우팅 비용 0 | 로컬 모델 설치·성능 확인이 추가되고, 한국어·일본어 분류 품질을 보장하기 어렵다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 단순 질문은 저가 모델로 끝난다. 모델 교체가 `.env` 수정으로 끝난다.
- 대가: 티어를 잘못 고르면 품질이 떨어진다 → 평가 데이터셋(PRD 10장)으로 바꾸기 전후를 비교한다.

## 재검토 조건
- 평가에서 Haiku 추출 정확도가 목표(80%)에 못 미칠 때 → 추출만 Sonnet으로 올린다
- 비용 측정 결과 생성 단계 비용이 크게 부담될 때
- 개발 중 토큰 비용 → 개발에는 로컬 Ollama를 쓴다 ([ADR-0012](0012-local-ollama-for-dev.md))
