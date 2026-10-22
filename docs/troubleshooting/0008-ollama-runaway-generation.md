# TS-0008: 로컬 Ollama로 유이 3과 수업 준비를 돌리면 "개인화 설명 쓰기"에서 10분 넘게 멈췄다
- 날짜: 2026-10-22
- 관련 모듈: `ai-server/app/agent/lesson_prep/llm.py` (`get_model`), `nodes.py` (`write_explanations`)
- 관련 ADR: 기술 [ADR-0012](../adr/0012-local-ollama-for-dev.md)

## 증상
유이(stu-1) 3과 수업 준비를 시작했더니 화면이 "다음 단계 진행 중"에서 10분 넘게 그대로였다. 에러 이벤트도 없었다. 서버를 다시 띄우고 해도 같았다. 2과 수업 준비는 문제없이 끝났었다.

- `GET /prep/{thread_id}/state` → `{"status":"running"}`
- LangSmith 추적: `load_profile`·`load_textbook`·`plan_lesson`은 몇 ms 만에 끝났고, `write_explanations` 아래 `ChatOllama` 호출 4개(범주별)가 전부 `running`
- `~/.ollama/logs/server.log`:

```
slot print_timing: id  0 | task 0 | n_gen =  13525, tg =  17.68 t/s, tg_3s =  15.78 t/s
[GIN] 2026/10/22 - 11:45:51 | 500 |        14m44s |       127.0.0.1 | POST     "/api/chat"
```

같은 로그에 10/21 17:15~17:39 23분짜리 500 요청도 있었다. 10/20까지(`server-1.log`, 요청 87개)는 2,000토큰을 넘긴 요청이 하나도 없었다.

## 원인
- 범주 4개 중 **숙제(homework)** 설명에서만 qwen3:8b가 같은 문단("練習問題では、動詞の後に…")을 계속 되풀이했다. `temperature=0`이라 한번 반복에 들어가면 빠져나오지 못한다.
- `get_model`이 Ollama에 출력 상한(`num_predict`)을 주지 않아 Ollama 기본값(-1, 무제한)이 적용됐다. 그래서 스스로 끝나지 않았다.
- Ollama 동시 처리 슬롯이 1개(`id 0`만 보임)라서 `run_parallel`로 동시에 보낸 나머지 범주 요청도 그 뒤에서 기다렸다.
- 처음에는 작업 중인 코드 변경(장별 대본 노드 추가 등) 때문인지 의심했다. 하지만 `write_explanations`·프롬프트·교재 데이터(`data/curriculum/ko1/unit_03.json`, 10/21 14:36 이후 그대로)는 바뀌지 않았다. 바뀐 것은 입력이었다. 예전에는 **2과**(연습 2개)를 준비했고, 이번에는 처음으로 **3과**(연습 문제 3개를 숙제로 배정)를 준비했다.

## 시도한 것
| 시도 | 결과 |
|---|---|
| 서버 로그(`.dev-logs/ai.log`, `api.log`) 확인 | 에러 없음. `/prep/start` 200 뒤로 아무 기록 없음 |
| 추적(`/traces/{id}`)으로 멈춘 노드 확인 | `write_explanations`의 LLM 호출 4개가 모두 진행 중 |
| Ollama 서버 로그 확인 | 한 요청이 13k~23k 토큰 생성 → 반복 생성 |
| `num_predict=4096`만 추가 | 무한 대기는 막지만 숙제 설명이 매번 상한에 걸려 오류로 끝난다 |
| 체크포인트 상태로 범주별 프롬프트를 다시 만들어 Ollama에 직접 호출 (`num_predict=1500`) | review 101, new_vocab 720, new_grammar 440 토큰으로 정상 종료. homework만 1500에서 `done_reason=length` |
| homework에 `repeat_penalty` 1.1 / 1.2 | 608 / 421 토큰에서 `stop`으로 정상 종료 |

## 해결
- `llm.py` `get_model`의 Ollama 분기에 두 가지를 넣었다.
  - `repeat_penalty=float(os.environ.get("OLLAMA_REPEAT_PENALTY", "1.1"))`: 반복을 막는다.
  - `num_predict=int(os.environ.get("OLLAMA_NUM_PREDICT", "4096"))`: 그래도 반복에 빠지면 무한히 기다리지 않고 오류(SSE `error`)로 끝낸다.
- `.env.example`에 두 값을 추가하고 ADR-0012 결정에 한 줄 보탰다.

## 배운 점 / 다음에 주의할 것
- 로컬 모델에는 출력 상한을 항상 준다. 클라우드 API는 `max_tokens`가 있지만 Ollama는 기본값이 무제한이다.
- `temperature=0`과 작은 모델을 같이 쓰면 반복 루프가 생길 수 있다. 특정 입력(이번에는 연습 문제 목록)에서만 나타나서, 다른 과에서 잘 돌았다고 안심하면 안 된다.
- "진행 중에서 안 넘어간다"면 추적의 `running` 노드 → `~/.ollama/logs/server.log`의 `n_gen` 순서로 본다. 범주별로 직접 호출해 보면 어느 입력이 문제인지 바로 나온다.
- 멈춘 SSE 연결이 열려 있으면 uvicorn `--reload`가 `Waiting for connections to close`에서 멈춘다. 이때는 dev.sh를 다시 띄운다.
- Spring 쪽 `OllamaChatOptions`(채팅)도 같은 위험이 있다. 채팅 답변이 멈추면 같은 옵션을 넣는다.
