"""
이 파일의 역할: LLM을 부르는 데 필요한 것들을 한곳에 모아 둔다.

- .env에서 API 키와 모델 이름 읽기
- prompts/ 폴더의 프롬프트 파일을 읽고 빈칸 채우기
- LLM을 불러 "구조화된 출력"(pydantic 형식)을 dict로 받기
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from app.agent.lesson_prep.textbook import PROJECT_DIR

# 모노레포 루트의 .env를 환경변수로 불러온다 (ANTHROPIC_API_KEY, LLM_MODEL_QUALITY 등)
load_dotenv(PROJECT_DIR.parent / ".env")

PROMPT_DIR = PROJECT_DIR / "prompts"
# 모델 티어 (ADR-0007): fast = 추출·검증 같은 단순 판단, quality = 설명·대본·브리핑 같은 생성
DEFAULT_MODELS = {"fast": "anthropic:claude-haiku-5-5", "quality": "anthropic:claude-sonnet-5-5"}
MODEL_ENV_KEYS = {"fast": "LLM_MODEL_FAST", "quality": "LLM_MODEL_QUALITY"}

# 언어 코드를 프롬프트에 쓸 언어 이름으로 바꾸는 표
LANG_NAMES = {"ja": "일본어", "en": "영어"}


def load_prompt(name: str, values: dict) -> str:
    """
    prompts/<name>.md 파일을 읽고, {키} 모양의 빈칸을 values의 값으로 바꾼다.
    예: "{lesson_minutes}" -> "50"
    """
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


@lru_cache
def get_model(tier: str):
    """티어에 맞는 모델을 만든다. 한 번 만든 모델은 다시 쓴다 (요청마다 만들지 않음)."""
    # "제공자:모델이름" 형식이라 .env의 LLM_MODEL_FAST / LLM_MODEL_QUALITY만 바꾸면 다른 모델을 쓸 수 있다
    model = os.environ.get(MODEL_ENV_KEYS[tier], DEFAULT_MODELS[tier])
    if model.startswith("ollama:"):
        # 로컬 Ollama (ADR-0012): 기본 컨텍스트 4096 토큰은 교재 목록이 든 프롬프트를 잘라 버리므로 늘리고,
        # qwen3의 생각(thinking) 출력은 시간만 늘리므로 끈다.
        # repeat_penalty: temperature=0에서 qwen3가 같은 문단을 끝없이 되풀이하는 것을 막는다 (TS-0008, 숙제 설명에서 재현)
        # num_predict: 그래도 반복에 빠지면 무한히 기다리지 않고 오류로 끝나게 하는 출력 상한
        return init_chat_model(
            model,
            num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
            num_predict=int(os.environ.get("OLLAMA_NUM_PREDICT", "4096")),
            repeat_penalty=float(os.environ.get("OLLAMA_REPEAT_PENALTY", "1.1")),
            reasoning=False,
            temperature=0,
        )
    return init_chat_model(model)


def call_llm(prompt_name: str, output_schema, values: dict, tier: str = "quality", system: str | None = None) -> dict:
    """
    프롬프트 파일에 값을 채워 LLM을 부르고, 결과를 dict로 돌려준다.
    output_schema(pydantic 클래스)를 주면 LLM이 그 형식에 맞춰 답한다.
    tier: "fast"(저가 모델) 또는 "quality"(고품질 모델)
    system: 시스템 프롬프트 파일 이름 (prompts/<system>.md). 역할·규칙처럼 질문마다 바뀌지 않는 부분을 둔다
    """
    prompt = load_prompt(prompt_name, values)
    if system:
        prompt = [("system", load_prompt(system, values)), ("human", prompt)]
    # method="json_schema": 모델이 정해진 JSON 형식으로만 답하게 하는 방식 (최신 Claude 모델의 권장 방식)
    structured_model = get_model(tier).with_structured_output(output_schema, method="json_schema")
    # LangSmith 추적에서 프롬프트 이름으로 보이게 한다 (기술 ADR-0028). 추적이 꺼져 있으면 아무 일도 안 한다
    config = {
        "run_name": prompt_name,
        "tags": [tier],
        "metadata": {"prompt": prompt_name, "tier": tier, "model": os.environ.get(MODEL_ENV_KEYS[tier], DEFAULT_MODELS[tier])},
    }
    result = structured_model.invoke(prompt, config=config)
    return result.model_dump()
