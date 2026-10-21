"""
이 파일의 역할: 모든 수업에 쓰는 고정된 7단계 수업 틀. (기획 ADR-0015, ADR-0015)

틀(순서·시간·할 일)은 코드에 고정하고, 학생마다 바뀌는 "내용"만 채운다.
  - 범주(review / new_vocab / new_grammar / homework)의 설명·예문 → 해당 단계에 들어간다
  - 워밍업 질문, 활용 활동 → 브리핑(LLM)이 채운다
  - 오류 피드백 → 수업 중에 생기므로 할 일만 적는다

50분 기준 시간을 수업 길이에 비례해서 늘리거나 줄인다.
"""

from app.agent.lesson_prep.schemas import CATEGORIES

# (단계 키, 이름, 50분 기준 시간, 할 일, 이 단계에 들어가는 범주)
STEPS = [
    ("warmup", "워밍업 및 안부", 5, "근황 대화로 분위기를 만들고, 지난 수업 표현을 자연스럽게 쓰게 한다.", []),
    ("review", "복습", 5, "지난 시간 핵심 표현 2~3개를 퀴즈나 짧은 질문으로 확인한다.", ["review"]),
    ("present", "새 내용 도입", 10, "오늘의 목표를 한 문장으로 제시 → 그림·대화로 맥락 → 어휘·문법 설명. 설명은 짧게, 예문은 충분히.", ["new_vocab", "new_grammar"]),
    ("drill", "통제된 연습", 10, "교체 연습, 문장 완성, 빈칸 채우기. 즉시 피드백하고 발음·억양도 잡는다.", ["new_grammar"]),
    ("activity", "의미 있는 활용 활동", 12, "롤플레이, 자기 이야기 말하기. 오류는 끊지 않고 메모해 둔다.", []),
    ("feedback", "오류 피드백", 5, "메모한 오류 2~3개를 학생이 스스로 고쳐 보게 한 뒤 정리한다.", []),
    ("wrapup", "마무리 및 과제", 3, "오늘 배운 표현을 한 문장으로 말해 보게 하고, 과제를 내고 다음 수업을 예고한다.", ["homework"]),
]
BASE_MINUTES = 50
VOCAB_SHARE_OF_PRESENT = 0.4  # "새 내용 도입" 중 어휘에 쓰는 비율 (나머지는 문법)


def step_minutes(lesson_minutes: int, has_review: bool = True) -> dict:
    """단계별 시간. 복습할 게 없으면 복습 시간을 통제된 연습에 준다. 반올림 오차는 활용 활동에 몰아 합계를 맞춘다."""
    minutes = {key: round(base * lesson_minutes / BASE_MINUTES) for key, _, base, _, _ in STEPS}
    if not has_review:
        minutes["drill"] += minutes["review"]
        minutes["review"] = 0
    minutes["activity"] += lesson_minutes - sum(minutes.values())
    return minutes


def category_minutes(steps: dict) -> dict:
    """단계 시간에서 범주별 시간을 계산한다. 범주에 속하지 않는 단계(워밍업·활용·피드백)는 빠진다."""
    vocab = round(steps["present"] * VOCAB_SHARE_OF_PRESENT)
    return {
        "review": steps["review"],
        "new_vocab": vocab,
        "new_grammar": steps["present"] - vocab + steps["drill"],
        "homework": steps["wrapup"],
    }


def frame_only_minutes(steps: dict) -> int:
    """범주에 속하지 않는 단계의 시간 합계."""
    return sum(steps[key] for key, *_ , cats in STEPS if not cats)


def assemble(lesson_minutes: int, drafts: dict, briefing: dict | None) -> list[dict]:
    """틀에 내용을 채운 최종 수업안. 범주 내용은 키로만 가리키고(화면이 drafts에서 꺼내 씀), 브리핑 칸은 그대로 넣는다."""
    briefing = briefing or {}
    has_review = bool(drafts.get("review", {}).get("item_ids"))
    minutes = step_minutes(lesson_minutes, has_review)
    extra = {
        "warmup": briefing.get("warmup_questions", []),
        "activity": [briefing["practice_activity"]] if briefing.get("practice_activity") else [],
        "feedback": [],
    }
    steps = [
        {
            "key": key,
            "name": name,
            "minutes": minutes[key],
            "guide": guide,
            "categories": [c for c in cats if c in CATEGORIES],
            "items": extra.get(key, []),
        }
        for key, name, _, guide, cats in STEPS
    ]
    # 문화는 새 문법·대화문을 배울 때 함께 다룬다 (기획 ADR-0023). 화면은 briefing.culture[culture]를 그린다
    next(s for s in steps if s["key"] == "present")["culture"] = 0 if briefing.get("culture") else None
    return steps
