"""
이 파일의 역할: 그래프의 노드 함수들을 모아 둔다.

노드는 모두 "State를 받아서, 바꿀 값만 dict로 돌려주는 일반 함수"다.
그래프에 연결하지 않고도 함수만 따로 불러서 시험해 볼 수 있다.

  코드 노드 (정해진 대로만 동작): load_profile, load_textbook, plan_lesson
  LLM 노드 (LLM이 판단):          write_explanations, write_scripts, auto_review, briefing, write_slides, write_slide_scripts
  사람 노드 (선생님이 판단):       human_review
"""

import json
from langgraph.types import interrupt
from langsmith.utils import ContextThreadPoolExecutor

from app.agent.lesson_prep import lesson_frame, llm
from app.agent.lesson_prep.schemas import (
    CATEGORIES,
    CATEGORY_NAMES,
    BriefingCulture,
    BriefingGrammar,
    BriefingLearner,
    BriefingPersonal,
    ExplanationOutput,
    LessonPlan,
    ReviewResult,
    ScriptOutput,
    SlidePlanOutput,
    SlideScriptOutput,
    StudentProfile,
    TeacherBriefing,
)
from app.agent.lesson_prep.textbook import all_items_by_id, format_item_for_prompt, get_data_dir, load_all_items
from app.curriculum.ids import to_new
from app.curriculum.sheets import BOOK_SOURCES, load_sheet
from app.rag import index as rag_index
from app.standard import l1_notes



# ---------------------------------------------------------------------------
# 작은 도우미 함수들
# ---------------------------------------------------------------------------


def to_json(data) -> str:
    """dict/list를 사람이 읽기 쉬운 JSON 글로 바꾼다. (프롬프트에 넣을 때 사용)"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def items_text(item_ids: list[str], items: dict) -> str:
    """항목 ID 목록을 프롬프트에 넣을 교재 원문 글로 바꾼다."""
    texts = [format_item_for_prompt(items[i]) for i in item_ids if i in items]
    return "\n".join(texts) if texts else "(없음)"


def learned_ids(profile: dict) -> set:
    """
    학생이 과거에 배운 모든 항목 ID를 모은다.
    약점으로 등록된 항목도 넣는다. 이 서비스 밖에서 배운 학생(체험 수업 뒤 등록 등)은 수업 기록이 없어도
    약점은 있으므로, 그대로 두면 약점이 복습에서 빠진다.
    """
    ids = set(profile["weaknesses"])
    for record in profile["lesson_history"]:
        ids.update(record["item_ids"])
    return ids


def run_parallel(func, categories: list, max_workers: int | None = None) -> dict:
    """서로 독립인 LLM 호출(범주별, 브리핑 조각별)을 동시에 실행하고 {키: 결과}로 돌려준다 (참고노트 5-2)."""
    if not categories:
        return {}
    # 일반 ThreadPoolExecutor는 실행 맥락(contextvars)을 넘기지 않아, 병렬 LLM 호출이 LangSmith에서
    # 그래프와 따로 떨어진 trace로 흩어진다. 맥락을 복사해 주는 실행기를 쓴다 (기술 ADR-0028)
    with ContextThreadPoolExecutor(max_workers=max_workers or len(categories)) as pool:
        return dict(zip(categories, pool.map(func, categories)))


# ---------------------------------------------------------------------------
# 1~2. 로드 노드 (코드)
# ---------------------------------------------------------------------------


def load_profile(state: dict) -> dict:
    """
    학생 프로필을 준비한다.
    State에 profile이 이미 들어 있으면(API 실행: Spring이 DB에서 꺼내 보냄) 형식만 검사해서 쓰고,
    없으면(CLI·테스트) data/students/ 의 JSON 파일을 읽는다.
    """
    if state.get("profile"):
        return {"profile": with_new_ids(StudentProfile.model_validate(state["profile"]).model_dump())}
    path = get_data_dir() / "students" / f"{state['student_id']}.json"
    with open(path, encoding="utf-8") as f:
        profile = StudentProfile.model_validate(json.load(f))  # 형식 검사
    return {"profile": with_new_ids(profile.model_dump())}


def with_new_ids(profile: dict) -> dict:
    """옛 교재 ID(u02-g01)가 남아 있으면 단원 시트 ID로 바꾼다 (DB 이전 전 기록·샘플 프로필, 기술 ADR-0032)."""
    profile["weaknesses"] = [to_new(i) for i in profile["weaknesses"]]
    for record in profile["lesson_history"]:
        record["item_ids"] = [to_new(i) for i in record["item_ids"]]
        record["understanding"] = {to_new(k): v for k, v in record.get("understanding", {}).items()}
    return profile


class MissingUnitSheet(ValueError):
    """고른 과의 단원 시트가 없다 (다시 해도 같다 → retryable=false)"""


def load_textbook(state: dict) -> dict:
    """
    이번에 배울 과의 단원 시트를 읽고, 학생이 과거에 배운 항목(복습 후보)도 모은다 (기술 ADR-0032).
    교재·과는 선생님이 실행할 때 고른 값, 없으면 프로필의 next_book·next_unit.
    """
    profile = state["profile"]
    book = state.get("book") or profile.get("next_book") or "ko1"
    unit_no = state.get("unit_no") or profile["next_unit"]
    unit = load_sheet(book, unit_no)
    if unit is None:
        title = BOOK_SOURCES.get(book, {}).get("title", book)
        raise MissingUnitSheet(f"「{title}」 {unit_no}과의 단원 시트가 없어요. python -m app.curriculum.build {book} 로 만들 수 있어요.")

    # 과거에 배운 항목의 원문을 다른 과의 시트에서 찾아온다 (같은 표준 항목은 이번 과의 것을 쓴다)
    learned = learned_ids(profile)
    current = {item["id"] for kind in ("vocabulary", "grammar", "dialogues", "readings", "exercises") for item in unit[kind]}
    past_items = [item for item_id, item in load_all_items().items() if item_id in learned and item_id not in current]

    return {"book": book, "unit_no": unit_no, "textbook_unit": unit, "past_items": past_items}


# ---------------------------------------------------------------------------
# 3. plan_lesson (코드): 4개 범주의 구성안 만들기
#    진도와 시간 배분에는 정답 규칙이 있으므로 LLM에 맡기지 않는다 (ADR-0013).
#    선생님이 검토 화면에서 고칠 수 있다.
# ---------------------------------------------------------------------------

MAX_REVIEW_ITEMS = 5  # 복습에 넣을 최대 항목 수
REVIEW_KINDS = ("vocab", "grammar")  # 복습은 어휘·문법만 (대화문·연습문제는 제외)


def last_understanding(profile: dict) -> dict:
    """직전 수업에서 선생님이 승인한 항목별 이해도 {항목 ID: confused | shaky | ok} (기술 ADR-0033)."""
    return profile["lesson_history"][-1].get("understanding", {}) if profile["lesson_history"] else {}


def long_review(profile: dict, review_ids: list[str]) -> bool:
    """직전 수업에서 헷갈린 항목을 복습하면 복습 시간을 늘린다."""
    understanding = last_understanding(profile)
    return any(understanding.get(i) == "confused" for i in review_ids)


def pick_review(profile: dict, past_items: dict) -> tuple[list[str], str]:
    """
    직전 수업에서 헷갈림 → 조금 헷갈림 → 약점(배운 것만) → 직전 수업의 문법 → 어휘 순서로 복습 항목을 고른다.
    이해도는 수업 후 기록에서 선생님이 승인한 것이다 (기획 ADR-0029).
    """
    reviewable = lambda i: i in past_items and past_items[i]["kind"] in REVIEW_KINDS  # noqa: E731
    understanding = last_understanding(profile)
    confused = [i for i, level in understanding.items() if level == "confused" and reviewable(i)]
    shaky = [i for i, level in understanding.items() if level == "shaky" and reviewable(i)]
    weak = [i for i in profile["weaknesses"] if reviewable(i)]

    last_ids = profile["lesson_history"][-1]["item_ids"] if profile["lesson_history"] else []
    rest = [i for kind in ("grammar", "vocab") for i in last_ids if reviewable(i) and past_items[i]["kind"] == kind]

    picked = list(dict.fromkeys(confused + shaky + weak + rest))[:MAX_REVIEW_ITEMS]  # 순서를 지키며 중복 제거
    groups = [("지난 수업에서 헷갈림", confused), ("조금 헷갈림", shaky), ("약점", weak), ("직전 수업 항목", rest)]
    parts, counted = [], set()
    for name, ids in groups:
        n = len([i for i in picked if i in ids and i not in counted])
        counted.update(i for i in picked if i in ids)
        if n:
            parts.append(f"{name} {n}개")
    return picked, " + ".join(parts)


def plan_lesson(state: dict) -> dict:
    """교재와 프로필을 보고 범주별 항목, 시간, 이유를 정한다. (코드 규칙)"""
    unit = state["textbook_unit"]
    past_items = {item["id"]: item for item in state["past_items"]}

    review_ids, review_reason = pick_review(state["profile"], past_items)
    vocab_ids = [v["id"] for v in unit["vocabulary"]]  # 교재 제시 순서 그대로
    grammar_ids = [g["id"] for g in unit["grammar"]]
    # 숙제: 문법 수만큼 앞쪽 연습문제 (교재 연습문제는 문법 순서대로 나온다)
    homework_ids = [e["id"] for e in unit["exercises"]][: max(1, len(grammar_ids))]
    # 시간은 고정된 15장 슬라이드 틀에서 나온다 (워밍업·목표 대화·역할극·고치기 단계는 범주에 속하지 않는다)
    steps = lesson_frame.step_minutes(state["lesson_minutes"], long_review(state["profile"], review_ids))
    minutes = lesson_frame.category_minutes(steps, bool(review_ids))

    unit_title = f"{unit['unit_no']}과 {unit['title']}"
    plan = {
        "review": {"item_ids": review_ids, "minutes": minutes["review"], "reason": review_reason or "복습할 항목 없음"},
        "new_vocab": {"item_ids": vocab_ids, "minutes": minutes["new_vocab"], "reason": f"{unit_title} 어휘 {len(vocab_ids)}개, 교재 순서대로"},
        "new_grammar": {"item_ids": grammar_ids, "minutes": minutes["new_grammar"], "reason": f"{unit_title} 문법 {len(grammar_ids)}개"},
        "homework": {"item_ids": homework_ids, "minutes": minutes["homework"], "reason": "이번 과 문법 연습문제"},
    }
    return {"plan": LessonPlan.model_validate(plan).model_dump()}


# ---------------------------------------------------------------------------
# 4. 범주별 생성 (LLM): 개인화 설명 -> 대본
#    승인된 범주는 건드리지 않고, 나머지 범주만 (다시) 만든다.
# ---------------------------------------------------------------------------


def write_explanations(state: dict) -> dict:
    """승인되지 않은 범주마다 개인화 설명을 만든다."""
    items = all_items_by_id(state)
    approved = state.get("approved_categories", [])
    feedback = state.get("human_feedback", {})
    drafts = dict(state.get("drafts", {}))  # 기존 초안을 복사해서 필요한 범주만 바꾼다

    def generate(category: str) -> dict:
        plan = state["plan"][category]
        old_draft = drafts.get(category)  # 이전 초안 (처음이면 None)
        values = {
            "category_name": CATEGORY_NAMES[category],
            "lang_name": llm.LANG_NAMES[state["target_lang"]],
            "profile": to_json(state["profile"]),
            "minutes": plan["minutes"],
            "reason": plan["reason"],
            "items": items_text(plan["item_ids"], items),
            "previous_draft": old_draft["explanation"] if old_draft else "(없음)",
            "feedback": feedback.get(category, "(없음)"),
        }
        return llm.call_llm("write_explanation", ExplanationOutput, values)

    # 승인된 범주는 그대로 두고, 나머지 범주만 동시에 만든다
    targets = [c for c in CATEGORIES if c not in approved]
    # 0분 범주(예: 첫 수업의 복습)는 LLM을 부르지 않고 비워 둔다.
    # 내용을 쓰면 auto_review의 "대본 분량"에서 계속 실패해 재시도가 반복된다.
    outputs = run_parallel(generate, [c for c in targets if not is_empty(state["plan"][c])])

    for category in targets:
        plan = state["plan"][category]
        old_draft = drafts.get(category)
        output = outputs.get(category, {"explanation": "", "examples": []})
        # 구성안(항목, 시간, 이유) + 새 설명. 대본은 다음 노드가 채운다.
        drafts[category] = {
            "item_ids": plan["item_ids"],
            "minutes": plan["minutes"],
            "reason": plan["reason"],
            "explanation": output["explanation"],
            "examples": output["examples"],
            "script": old_draft["script"] if old_draft and not is_empty(plan) else "",
        }

    return {"drafts": drafts}


def is_empty(plan_or_draft: dict) -> bool:
    """시간이 배정되지 않은 범주인가."""
    return plan_or_draft["minutes"] == 0


def write_scripts(state: dict) -> dict:
    """승인되지 않은 범주마다 대본을 만든다. (설명이 먼저 만들어져 있어야 한다)"""
    items = all_items_by_id(state)
    approved = state.get("approved_categories", [])
    feedback = state.get("human_feedback", {})
    drafts = dict(state["drafts"])

    def generate(category: str) -> dict:
        draft = drafts[category]
        values = {
            "category_name": CATEGORY_NAMES[category],
            "lang_name": llm.LANG_NAMES[state["target_lang"]],
            "profile": to_json(state["profile"]),
            "minutes": draft["minutes"],
            "items": items_text(draft["item_ids"], items),
            "explanation": draft["explanation"],
            "previous_script": draft["script"] or "(없음)",
            "feedback": feedback.get(category, "(없음)"),
        }
        return llm.call_llm("write_script", ScriptOutput, values)

    targets = [c for c in CATEGORIES if c not in approved and not is_empty(drafts[c])]
    for category, output in run_parallel(generate, targets).items():
        drafts[category] = {**drafts[category], "script": output["script"]}

    # 피드백을 모두 반영했으므로 비운다
    return {"drafts": drafts, "human_feedback": {}}


# ---------------------------------------------------------------------------
# 5. auto_review: 코드로 확인할 수 있는 것은 코드로, 나머지는 LLM으로 검토
# ---------------------------------------------------------------------------


def code_checks(state: dict) -> list[dict]:
    """ID, 복습 항목, 시간 합계처럼 정답이 분명한 것을 코드로 점검한다."""
    drafts = state["drafts"]
    items = all_items_by_id(state)
    checks = []

    # (1) 참조한 항목 ID가 교재에 실제로 있는가
    missing = []
    for category in CATEGORIES:
        for item_id in drafts[category]["item_ids"]:
            if item_id not in items:
                missing.append(item_id)
    checks.append(
        {
            "name": "교재 항목 ID",
            "passed": not missing,
            "reason": f"교재에 없는 ID: {missing}" if missing else "모든 ID가 교재에 있습니다.",
        }
    )

    # (2) 복습 항목이 lesson_history에 실제로 있는가
    learned = learned_ids(state["profile"])
    not_learned = [i for i in drafts["review"]["item_ids"] if i not in learned]
    checks.append(
        {
            "name": "복습 항목",
            "passed": not not_learned,
            "reason": f"배운 적 없는 항목이 복습에 있음: {not_learned}"
            if not_learned
            else "복습 항목이 모두 수업 기록에 있습니다.",
        }
    )

    # (3) 범주 시간 + 틀에만 있는 단계(워밍업·목표 대화·역할극·고치기) 시간이 수업 시간과 같은가
    review_ids = drafts["review"]["item_ids"]
    steps = lesson_frame.step_minutes(state["lesson_minutes"], long_review(state["profile"], review_ids))
    total = sum(drafts[category]["minutes"] for category in CATEGORIES) + lesson_frame.frame_only_minutes(steps, bool(review_ids))
    checks.append(
        {
            "name": "시간 합계",
            "passed": total == state["lesson_minutes"],
            "reason": f"범주 시간 + 틀에만 있는 단계 시간 = {total}분, 수업 시간은 {state['lesson_minutes']}분입니다.",
        }
    )
    return checks


def auto_review(state: dict) -> dict:
    """
    체크리스트로 초안을 검토한다. 다시 만들지는 않고, 결과를 선생님 검토 화면에 붙여 넘긴다 (ADR-0021).
      - 코드 점검(ID, 복습, 시간 합계): 실패하면 경고. 구성안은 코드 규칙이라 다시 만들어도 같은 결과다.
      - LLM 점검(자연스러움, 수준 등): 참고 의견. 로컬 모델의 판정이 흔들려서 재시도의 근거로 쓰지 않는다.
    """
    drafts = state["drafts"]
    items = all_items_by_id(state)

    # LLM이 분량을 판단하기 쉽도록 대본 글자 수를 함께 알려준다
    drafts_for_prompt = {}
    all_ids = []
    for category in CATEGORIES:
        draft = drafts[category]
        drafts_for_prompt[CATEGORY_NAMES[category]] = {**draft, "script_length": len(draft["script"])}
        all_ids.extend(draft["item_ids"])

    values = {
        "lang_name": llm.LANG_NAMES[state["target_lang"]],
        "profile": to_json(state["profile"]),
        "items": items_text(all_ids, items),
        "drafts": to_json(drafts_for_prompt),
    }
    llm_result = llm.call_llm("auto_review", ReviewResult, values)

    code = [{**check, "kind": "code"} for check in code_checks(state)]
    advice = [{**check, "kind": "llm"} for check in llm_result["checks"]]
    passed = all(check["passed"] for check in code)  # 통과 여부는 코드 점검으로만 정한다

    return {
        "review_result": {"checks": code + advice, "passed": passed},
        "review_warning": not passed,
    }


# ---------------------------------------------------------------------------
# 5-1. briefing: 선생님이 수업 전에 읽을 브리핑 (ADR-0013)
#      코드가 근거 자료(교원용 지침서)를 먼저 모으고, LLM은 개인화 칸만 쓴다.
#      출처는 코드가 붙인다.
#      구성안이 정해진 뒤(자동 검토 뒤) 한 번만 만든다.
# ---------------------------------------------------------------------------

GUIDE_SECTIONS = ["학습 목표", "문법"]  # 브리핑 근거로 쓰는 구역 (학습 목표·수업 개요, 문법 1·2)


def guide_of(book: str) -> str:
    """교재 시리즈의 교원용 지침서 색인 ID (ko1 → ko1_guide)"""
    return BOOK_SOURCES.get(book, BOOK_SOURCES["ko1"])["guide"]


def collect_references(book: str, unit_no: int) -> list[dict]:
    """필터 경로: 이번 과의 지침서 구역을 가져온다. 색인이 없으면 빈 목록 (브리핑은 근거 없이 만든다)."""
    return rag_index.get_sections(guide_of(book), unit_no, GUIDE_SECTIONS)


CULTURE_BOOK = "culture1"  # 세종한국문화 1 (기획 ADR-0023)
L1_COUNTRY_EXAMPLE = {"ja": "일본에서도 나이로 부르는 말이 있어요?", "en": "Do people in your country do this too?"}


def collect_culture(unit: dict) -> list[dict]:
    """
    이번 과 주제(과 제목·대화문·어휘)로 세종학당 자료에서 문화 후보를 찾는다 (의미 경로, 기술 ADR-0023).
      - 세종한국문화 1에서 2개: 생활·전통 문화
      - 교원용 지침서의 같은 과에서 1개: 호칭·인사 같은 언어 문화
    임베딩 서버가 없으면 빈 목록 (브리핑은 문화 없이 만들고 화면이 "선생님이 채워 주세요"로 표시한다).
    """
    dialogue = " ".join(line["text"] for d in unit["dialogues"] for line in d["lines"])
    vocab = " ".join(v["word"] for v in unit["vocabulary"][:10])
    query = f"{unit['title']} {dialogue} {vocab}"
    try:
        found = rag_index.search(query, k=2, book=CULTURE_BOOK)
        found += rag_index.search(f"{query} 문화 예절 인사 호칭", k=1, book=guide_of(unit["book"]), unit=unit["unit_no"])
    except Exception:  # noqa: BLE001 — 검색은 덧붙이는 정보라 실패해도 수업 준비는 계속한다
        return []
    return [
        {"book": r["book"], "pages": r["pages"], "source": r["source"], "excerpt": r["matched"].split("] ", 1)[-1]}
        for r in found
    ]


def culture_text(candidates: list[dict]) -> str:
    return "\n\n".join(f"[{i}] ({c['source']})\n{c['excerpt']}" for i, c in enumerate(candidates, 1))


def references_text(references: list[dict]) -> str:
    if not references:
        return "(없음)"
    return "\n\n".join(f"## {ref['source']}\n{ref['text']}" for ref in references)


def learner_view(profile: dict) -> str:
    """개인화 호출에 넣을 학생 정보. 교재 ID는 빼고 사람이 읽는 말만 남긴다 (작은 모델이 ID를 답에 섞지 않게)."""
    lines = [
        f"이름: {profile['name']}",
        f"수준: {profile['level']}",
        f"목표: {', '.join(profile['goals']) or '(없음)'}",
        f"관심사: {', '.join(profile.get('interests', [])) or '(없음)'}",
        f"약점 메모: {', '.join(profile.get('weakness_notes', [])) or '(없음)'}",
        f"선생님 메모: {profile.get('notes') or '(없음)'}",
    ]
    return "\n".join(lines)


def grammar_forms(item_ids: list[str], items: dict) -> str:
    return ", ".join(f"'{items[i]['form']}'" for i in item_ids if i in items) or "(없음)"


def briefing(state: dict) -> dict:
    """
    근거를 모으고 브리핑을 만든다. 출처와 수업 틀은 코드가 붙인다.
      - 문법 설명 포인트: 지침서 근거 + LLM (briefing_grammar)
      - 모국어별 실수·예상 질문·설명 팁: 검수 데이터에서 꺼낸다 (ADR-0022). 데이터에 없는 문법만 LLM (briefing_learner)
      - 워밍업·활용 활동·맞춤 팁: LLM (briefing_personal)
    """
    items = all_items_by_id(state)
    drafts = state["drafts"]
    profile = state["profile"]
    native = profile["native_language"]
    unit = state["textbook_unit"]
    references = collect_references(unit["book"], state["unit_no"])
    grammar_ids = drafts["new_grammar"]["item_ids"]
    weak_forms = grammar_forms([i for i in profile["weaknesses"] if items.get(i, {}).get("kind") == "grammar"], items)
    notes, missing_ids = l1_notes.lookup(grammar_ids, native)
    culture_candidates = collect_culture(unit)

    calls = {
        "briefing_grammar": (
            BriefingGrammar,
            {"grammar_items": items_text(grammar_ids, items), "references": references_text(references)},
        ),
        "briefing_personal": (
            BriefingPersonal,
            {
                "learner": learner_view(profile),
                "unit_title": f"{unit['unit_no']}과 「{unit['title']}」",
                "grammar_forms": grammar_forms(grammar_ids, items),
                "lesson_minutes": state["lesson_minutes"],
            },
        ),
    }
    if missing_ids:  # 데이터에 없는 문법만 LLM에 맡긴다
        calls["briefing_learner"] = (
            BriefingLearner,
            {
                "native_lang_name": llm.LANG_NAMES.get(native, native),
                "level": profile["level"],
                "grammar_forms": grammar_forms(missing_ids, items),
                "weak_forms": weak_forms,
                "weakness_notes": ", ".join(profile.get("weakness_notes", [])) or "(없음)",
            },
        )
    if culture_candidates:
        calls["briefing_culture"] = (
            BriefingCulture,
            {
                "native_lang_name": llm.LANG_NAMES.get(native, native),
                "l1_country_example": L1_COUNTRY_EXAMPLE.get(native, L1_COUNTRY_EXAMPLE["en"]),
                "interests": ", ".join(profile.get("interests", [])) or "(없음)",
                "unit_title": f"{unit['unit_no']}과 「{unit['title']}」",
                "candidates": culture_text(culture_candidates),
            },
        )
    outputs = run_parallel(lambda name: llm.call_llm(name, calls[name][0], calls[name][1]), list(calls))

    result = {**outputs["briefing_grammar"], **outputs["briefing_personal"]}
    generated = outputs.get("briefing_learner", {"common_mistakes": [], "expected_qa": []})
    result["common_mistakes"] = [m for note in notes for m in note["common_mistakes"]] + generated["common_mistakes"]
    result["expected_qa"] = [qa for note in notes for qa in note["expected_qa"]] + generated["expected_qa"]
    result["tips"] = [f"[{note['form']}] {note['explain_tip']}" for note in notes if note.get("explain_tip")] + result["tips"]

    # 모국어 칸의 출처: 검수됨 / Claude 초안(검수 전) / 실행 중 LLM 생성 — 화면이 표시를 나눈다
    l1_sources = [{"form": note["form"], "origin": "reviewed" if note["reviewed"] else "draft"} for note in notes]
    l1_sources += [{"form": items[i]["form"], "origin": "llm"} for i in missing_ids if i in items]

    # 문화 후보: 출처·원문은 코드가, 요약·비교 질문은 LLM이. 문화 내용이 아닌 후보(요약이 빈 것)는 뺀다
    by_index = {n["index"]: n for n in outputs.get("briefing_culture", {"notes": []})["notes"]}
    culture = [
        {**c, **{k: by_index[i][k] for k in ("summary", "question_ko", "question_l1")}}
        for i, c in enumerate(culture_candidates, 1)
        if i in by_index and by_index[i]["summary"].strip()
    ]

    extra = {
        # book·pages: 화면의 "원문 열기"가 원본 PDF를 그 쪽으로 연다 (기술 ADR-0030)
        "references": [{"source": ref["source"], "section": ref["section"], "book": ref["book"], "pages": ref["pages"]} for ref in references],
        "l1_sources": l1_sources,
        "culture": culture,
        # 자동으로 만든 단원 시트면 화면이 "검수 전 단원"을 표시한다 (기획 ADR-0030)
        "unit_sheet": {"book": unit["book"], "unit_no": unit["unit_no"], "status": unit["status"], "notes": unit["notes"]},
    }
    return {"briefing": TeacherBriefing.model_validate(result).model_dump() | extra}


# ---------------------------------------------------------------------------
# 5-2. write_slides: 15장 슬라이드 구성안 (기획 ADR-0032, 기술 ADR-0034)
#      틀(번호·단계·레이아웃·시간)은 코드(lesson_frame), 학생 화면 문구와 교사 노트는 LLM 한 번.
#      선생님이 4범주를 고치면 슬라이드가 낡으므로, 승인할 때 초안이 달라졌으면 한 번 더 만든다.
# ---------------------------------------------------------------------------


def slide_table_text(frame: list[dict]) -> str:
    return "\n".join(f"{s['no']}번 | {s['name']} | {s['minutes']}분 | 레이아웃 {s['layout']}" for s in frame)


def example_sentences(drafts: dict) -> str:
    """4범주 초안에 쓰인 한국어 예문 (슬라이드는 새 예문을 만들지 않고 이 안에서 고른다, 기획 ADR-0017)."""
    sentences = list(dict.fromkeys(e["korean"] for c in CATEGORIES for e in drafts[c]["examples"]))
    return "\n".join(f"- {s}" for s in sentences) or "(없음)"


def write_slides(state: dict) -> dict:
    """승인 전 4범주 초안과 브리핑을 재료로 15장 슬라이드 구성안(학생 화면 문구 + 교사 노트)을 만든다."""
    items = all_items_by_id(state)
    drafts = state["drafts"]
    briefing_ = state["briefing"]
    profile = state["profile"]
    unit = state["textbook_unit"]
    review_ids = drafts["review"]["item_ids"]
    long = long_review(profile, review_ids)
    frame = lesson_frame.frame(state["lesson_minutes"], bool(review_ids), long)

    values = {
        "lang_name": llm.LANG_NAMES[state["target_lang"]],
        "learner": learner_view(profile),
        "unit_title": f"{unit['unit_no']}과 「{unit['title']}」",
        "lesson_minutes": state["lesson_minutes"],
        "slide_table": slide_table_text(frame),
        "review_state": "복습할 항목이 있다" if review_ids else "복습할 이전 수업 정보가 없다 (2번은 수준 확인 질문으로 쓴다)",
        "review_items": items_text(review_ids, items),
        "vocab_items": items_text(drafts["new_vocab"]["item_ids"], items),
        "grammar_items": items_text(drafts["new_grammar"]["item_ids"], items),
        "dialogue_items": items_text([d["id"] for d in unit["dialogues"]], items),
        "homework_items": items_text(drafts["homework"]["item_ids"], items),
        "examples": example_sentences(drafts),
        "warmup_questions": "\n".join(f"- {q}" for q in briefing_.get("warmup_questions", [])) or "(없음)",
        "practice_activity": briefing_.get("practice_activity") or "(없음)",
        "grammar_points": to_json(briefing_.get("grammar_points", [])),
        "expected_qa": to_json(briefing_.get("expected_qa", [])),
    }
    output = SlidePlanOutput.model_validate(llm.call_llm("write_slides", SlidePlanOutput, values)).model_dump()
    slide_plan = lesson_frame.merge(state["lesson_minutes"], bool(review_ids), long, output)
    return {
        "briefing": {**briefing_, "slide_plan": slide_plan},
        "slides_fingerprint": lesson_frame.drafts_fingerprint(drafts),
    }


SCRIPT_WORKERS = 5  # 장별 대본은 15번 부르므로 한꺼번에 부르는 수를 줄인다 (로컬 모델 보호)


def slide_materials(slide: dict, state: dict, items: dict) -> str:
    """슬라이드 한 장의 대본 재료: 연결된 범주의 교재 원문·설명·4범주 대본, 범주가 없는 장은 브리핑과 예문."""
    drafts = state["drafts"]
    parts = []
    for category in slide["categories"]:
        draft = drafts[category]
        parts.append(
            f"[{CATEGORY_NAMES[category]}]\n교재 항목:\n{items_text(draft['item_ids'], items)}\n"
            f"개인화 설명:\n{draft['explanation'] or '(없음)'}\n수업 대본(참고):\n{draft['script'] or '(없음)'}"
        )
    briefing_ = state["briefing"]
    if slide["stage"] == "warmup":
        parts.append("워밍업 질문 후보:\n" + ("\n".join(f"- {q}" for q in briefing_.get("warmup_questions", [])) or "(없음)"))
    if slide["stage"] == "goal_dialog":
        parts.append("교재 대화문:\n" + items_text([d["id"] for d in state["textbook_unit"]["dialogues"]], items))
    if slide["stage"] == "activity":
        parts.append(f"활용 활동 후보: {briefing_.get('practice_activity') or '(없음)'}\n쓸 수 있는 예문:\n{example_sentences(drafts)}")
    return "\n\n".join(parts) or "(이 슬라이드에는 따로 연결된 재료가 없습니다. 학생 화면 문구와 교사 노트만 씁니다)"


def write_slide_scripts(state: dict) -> dict:
    """15장 슬라이드마다 선생님이 그대로 읽을 대본을 만든다. 한 장이 실패해도 나머지는 유지한다 (기술 ADR-0035)."""
    items = all_items_by_id(state)
    plan = state["briefing"]["slide_plan"]
    slides = plan["slides"]
    by_no = {s["no"]: s for s in slides}
    lang_name = llm.LANG_NAMES[state["target_lang"]]

    def generate(no: int) -> dict | None:
        slide = by_no[no]
        following = by_no.get(no + 1)
        values = {
            "learner": learner_view(state["profile"]),
            "lang_name": lang_name,
            "lesson_goal": plan["lesson_goal"],
            "final_mission": plan["final_mission"],
            "slide_no": no,
            "stage_name": slide["name"],
            "layout": slide["layout"],
            "minutes": slide["minutes"],
            "max_lines": lesson_frame.max_script_lines(slide["minutes"]),
            "activity": slide["activity"] or "(없음)",
            "student_screen": "\n".join(f"  - {t}" for t in slide["student_screen"]) or "  (비어 있음)",
            "note": to_json(slide["note"]),
            "slide_needs_check": ", ".join(slide["needs_check"]) or "(없음)",
            "materials": slide_materials(slide, state, items),
            "next_slide": f"{following['no']}번 {following['name']}: {following['activity']}" if following else "(마지막 슬라이드입니다)",
        }
        try:
            return SlideScriptOutput.model_validate(llm.call_llm("write_slide_script", SlideScriptOutput, values)).model_dump()
        except Exception:  # 한 장의 실패가 수업 준비 전체를 막지 않게 한다. 그 장은 확인 필요로 표시한다
            return None

    scripts = run_parallel(generate, [s["no"] for s in slides], max_workers=SCRIPT_WORKERS)

    new_slides = []
    for slide in slides:
        output = scripts[slide["no"]]
        if output is None:
            new_slides.append({**slide, "script": None, "needs_check": [*slide["needs_check"], "대본이 만들어지지 않았어요. 직접 쓰거나 다시 만들어 주세요."]})
        else:
            extra = output.pop("needs_check")
            new_slides.append({**slide, "script": output, "needs_check": [*slide["needs_check"], *extra]})

    checks = [c for c in plan["checks"] if c["name"] not in lesson_frame.SCRIPT_CHECK_NAMES] + lesson_frame.script_checks(new_slides)
    return {"briefing": {**state["briefing"], "slide_plan": {**plan, "slides": new_slides, "checks": checks}}}


# ---------------------------------------------------------------------------
# 6. human_review: 선생님이 범주별로 승인 / 직접 수정 / 피드백
# ---------------------------------------------------------------------------


def human_review(state: dict) -> dict:
    """
    그래프를 멈추고 선생님의 결정을 기다린다.

    재개할 때 받는 값(decisions)의 모양:
      {"review":    {"action": "approve"},
       "new_vocab": {"action": "edit", "explanation": "고친 설명", "script": "고친 대본"},
       "homework":  {"action": "feedback", "feedback": "숙제를 더 짧게"}}

    주의: 재개하면 이 함수가 처음부터 다시 실행되므로, interrupt() 앞에는
    파일 저장 같은 부작용이 있는 코드를 두지 않는다.
    """
    # interrupt()에 넘긴 값이 선생님에게 보여줄 내용이 된다. 여기서 그래프가 멈춘다.
    decisions = interrupt(
        {
            "drafts": state["drafts"],
            "briefing": state.get("briefing"),
            "review_result": state.get("review_result"),
            "review_warning": state.get("review_warning", False),
            "approved_categories": state.get("approved_categories", []),
        }
    )

    # --- 여기부터는 선생님이 결정을 보내서 재개된 뒤에 실행된다 ---
    drafts = dict(state["drafts"])
    approved = list(state.get("approved_categories", []))
    feedback = {}

    for category, decision in decisions.items():
        action = decision["action"]

        if action == "edit":
            # 직접 수정: 선생님이 보낸 글로 그대로 덮어쓴다 (보내지 않은 쪽은 기존 것 유지)
            draft = dict(drafts[category])
            draft["explanation"] = decision.get("explanation", draft["explanation"])
            draft["script"] = decision.get("script", draft["script"])
            drafts[category] = draft

        if action in ("approve", "edit"):
            # 승인 또는 수정한 범주는 확정한다
            if category not in approved:
                approved.append(category)

        if action == "feedback":
            # 피드백: 이 범주만 다시 생성하도록 기록해 둔다
            feedback[category] = decision["feedback"]

    return {
        "drafts": drafts,
        "approved_categories": approved,
        "human_feedback": feedback,
        "human_started": True,  # 이후 다시 생성한 초안은 자동 검토 없이 선생님에게 바로 돌아온다
    }
