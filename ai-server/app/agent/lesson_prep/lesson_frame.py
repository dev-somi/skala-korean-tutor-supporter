"""
이 파일의 역할: 모든 수업에 쓰는 고정된 15장 슬라이드 구성안의 틀. (기획 ADR-0032, 기술 ADR-0034)
참고 기준: docs/reference/온라인_한국어_1대1_수업_PPT_제작_기준.md §3

틀(슬라이드 번호·단계·레이아웃·시간)은 코드에 고정하고, 학생마다 바뀌는 "내용"(학생 화면 문구, 교사 노트)은
write_slides 노드의 LLM이 채운다. 이 파일은 LLM을 부르지 않는다.

  - 4범주(review / new_vocab / new_grammar / homework)의 시간은 이 틀의 단계 시간에서 나온다
  - 50분 기준 시간을 수업 길이에 비례해서 늘리거나 줄인다
"""

import hashlib
import json

from app.agent.lesson_prep.schemas import CATEGORIES

# (단계 키, 이름, 50분 기준 시간, 이 단계의 슬라이드 번호, 이 단계에 들어가는 범주)
STAGES = [
    ("warmup", "안부와 워밍업", 4, [1], []),
    ("review", "지난 시간 복습", 3, [2], ["review"]),
    ("goal_dialog", "오늘의 목표와 짧은 대화", 3, [3], []),
    ("vocab", "핵심 어휘", 6, [4, 5], ["new_vocab"]),
    ("expression", "핵심 표현", 6, [6, 7], ["new_grammar"]),
    ("drill", "도움을 받는 연습", 10, [8, 9, 10], ["new_grammar"]),
    ("activity", "자기 이야기와 역할극", 12, [11, 12, 13], []),
    ("feedback", "오늘의 문장 고치기", 3, [14], []),
    ("wrapup", "마무리와 숙제", 3, [15], ["homework"]),
]
BASE_MINUTES = 50
SLIDE_COUNT = 15
VOCAB_SLIDES = (4, 5)  # 슬라이드당 단어 3~4개 (기준 §4)
MAX_WORDS_PER_SLIDE = 4
FEEDBACK_SLIDE = 14  # 수업 중에 나온 오류를 적는 빈 칸 (실제 발화가 없으면 학생 화면을 비워 둔다, 기준 §4)

# 학생 화면 레이아웃 5가지 (기준 §5): question 질문·도입 / vocab 어휘 / expression 표현 설명 / practice 연습·활동 / closing 피드백·마무리
LAYOUTS = {
    1: "question", 2: "question", 3: "practice",
    4: "vocab", 5: "vocab", 6: "expression", 7: "expression",
    8: "practice", 9: "practice", 10: "practice", 11: "practice", 12: "practice", 13: "practice",
    14: "closing", 15: "closing",
}


def step_minutes(lesson_minutes: int, long_review: bool = False) -> dict:
    """
    단계별 시간. 반올림 오차는 자기 이야기와 역할극(activity)에 몰아 합계를 맞춘다.
    복습할 항목이 없어도 복습 단계의 시간은 그대로다. 그 시간에 수준 확인 질문을 한다 (기준 §3).
    long_review: 지난 수업에서 헷갈린 항목을 복습하면 복습을 두 배로 하고, 늘린 만큼 역할극에서 뺀다 (기술 ADR-0033).
    """
    minutes = {key: round(base * lesson_minutes / BASE_MINUTES) for key, _, base, _, _ in STAGES}
    if long_review:
        extra = max(0, min(minutes["review"], minutes["activity"] - 1))  # 역할극은 1분 이상 남긴다
        minutes["review"] += extra
        minutes["activity"] -= extra
    minutes["activity"] += lesson_minutes - sum(minutes.values())
    return minutes


def category_minutes(steps: dict, has_review: bool = True) -> dict:
    """단계 시간에서 범주별 시간을 계산한다. 범주에 속하지 않는 단계(워밍업·목표 대화·역할극·고치기)는 빠진다."""
    return {
        "review": steps["review"] if has_review else 0,
        "new_vocab": steps["vocab"],
        "new_grammar": steps["expression"] + steps["drill"],
        "homework": steps["wrapup"],
    }


def frame_only_minutes(steps: dict, has_review: bool = True) -> int:
    """범주에 속하지 않는 단계의 시간 합계. 복습할 게 없으면 복습 단계(수준 확인 질문)도 여기에 들어간다."""
    total = sum(steps[key] for key, _, _, _, cats in STAGES if not cats)
    return total if has_review else total + steps["review"]


def slide_minutes(steps: dict) -> dict:
    """슬라이드 번호 -> 시간. 단계 시간을 그 단계의 슬라이드에 고르게 나누고, 남는 분은 앞 슬라이드부터 1분씩 준다."""
    result = {}
    for key, _, _, numbers, _ in STAGES:
        base, rest = divmod(steps[key], len(numbers))
        for i, no in enumerate(numbers):
            result[no] = base + (1 if i < rest else 0)
    return result


def frame(lesson_minutes: int, has_review: bool, long_review: bool = False) -> list[dict]:
    """내용이 비어 있는 15장 틀: [{no, stage, name, layout, minutes, categories}]. LLM이 쓴 내용은 merge가 붙인다."""
    steps = step_minutes(lesson_minutes, long_review)
    minutes = slide_minutes(steps)
    return [
        {
            "no": no,
            "stage": key,
            "name": name,
            "layout": LAYOUTS[no],
            "minutes": minutes[no],
            "categories": [c for c in cats if c in CATEGORIES and (c != "review" or has_review)],
        }
        for key, name, _, numbers, cats in STAGES
        for no in numbers
    ]


def merge(lesson_minutes: int, has_review: bool, long_review: bool, output: dict) -> dict:
    """
    틀에 LLM이 쓴 내용을 번호별로 붙여 최종 구성안을 만든다 (briefing["slide_plan"]).
    번호·단계·레이아웃·시간은 틀의 값을 쓴다. LLM이 빠뜨린 슬라이드는 비워 두고 확인 필요로 표시한다.
    """
    written = {s["no"]: s for s in output["slides"]}
    slides = []
    for base in frame(lesson_minutes, has_review, long_review):
        content = written.get(base["no"])
        if content is None:
            content = {
                "student_screen": [],
                "activity": "",
                "note": {"goal": "", "procedure": "", "qa": [], "if_struggle": "", "if_good": "", "source": ""},
                "needs_check": ["이 슬라이드의 내용이 만들어지지 않았어요. 직접 채워 주세요."],
            }
        slides.append({**base, **{k: content[k] for k in ("student_screen", "activity", "note", "needs_check")}})
    plan = {
        "lesson_goal": output["lesson_goal"],
        "final_mission": output["final_mission"],
        "slides": slides,
        "homework": output["homework"],
        "needs_check": output["needs_check"],
    }
    plan["checks"] = slide_checks(plan, lesson_minutes)
    return plan


def slide_checks(plan: dict, lesson_minutes: int) -> list[dict]:
    """정답이 분명한 것은 코드로 점검한다. 실패해도 다시 만들지 않고 화면에 경고로 보인다 (기술 ADR-0021과 같은 방식)."""
    slides = plan["slides"]
    checks = []

    numbers = [s["no"] for s in slides]
    checks.append(
        {
            "name": "슬라이드 구성",
            "passed": numbers == list(range(1, SLIDE_COUNT + 1)),
            "reason": f"슬라이드 {len(slides)}장" if numbers != list(range(1, SLIDE_COUNT + 1)) else "1~15장이 모두 있습니다.",
        }
    )

    total = sum(s["minutes"] for s in slides)
    checks.append({"name": "시간 합계", "passed": total == lesson_minutes, "reason": f"슬라이드 시간 합계 {total}분, 수업 시간 {lesson_minutes}분"})

    empty = [s["no"] for s in slides if (not s["student_screen"] and s["no"] != FEEDBACK_SLIDE) or not s["note"]["procedure"].strip()]
    checks.append(
        {
            "name": "빈 슬라이드",
            "passed": not empty,
            # 14장(고치기)은 수업 중에 채우므로 학생 화면이 비어도 된다
            "reason": f"학생 화면이나 진행이 비어 있음: {empty}" if empty else "모든 슬라이드에 학생 화면과 진행이 있습니다.",
        }
    )

    crowded = [s["no"] for s in slides if s["no"] in VOCAB_SLIDES and len(s["student_screen"]) > MAX_WORDS_PER_SLIDE]
    checks.append(
        {
            "name": "어휘 슬라이드 분량",
            "passed": not crowded,
            "reason": f"어휘가 {MAX_WORDS_PER_SLIDE}개를 넘는 슬라이드: {crowded}" if crowded else f"어휘 슬라이드마다 {MAX_WORDS_PER_SLIDE}개 이하입니다.",
        }
    )

    homework = plan["homework"]
    flagged = bool(homework.get("pages", "").strip()) or any("숙제" in text or "쪽" in text for text in plan["needs_check"])
    checks.append(
        {
            "name": "숙제 정보",
            "passed": flagged,
            "reason": "숙제 쪽수가 있거나 확인 필요로 표시했습니다." if flagged else "숙제 쪽수가 없는데 확인 필요 표시도 없습니다.",
        }
    )
    return checks


def drafts_fingerprint(drafts: dict) -> str:
    """4범주 초안이 바뀌었는지 알아보는 지문. 슬라이드를 만든 뒤 선생님이 고쳤으면 승인 때 슬라이드를 다시 만든다."""
    text = json.dumps(drafts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
