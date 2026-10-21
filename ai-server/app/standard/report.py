"""
이 파일의 역할: 학습자별 진도·향상 리포트 (기획 ADR-0019, 기술 ADR-0018).

Spring이 학생의 승인된 수업 기록과 약점을 보내면, 표준 등급 목록으로 숫자를 계산해 돌려준다.
숫자와 문장은 모두 코드가 만든다. LLM을 쓰지 않는다 (없는 성과를 지어내지 않게).

- 배운 문법: 다룬 교재 항목 → 대응표(textbook_map) → 표준 문법 항목
- 배운 어휘: 다룬 교재 어휘의 글자 → 표준 어휘 등급 (교재 어휘 칸이 "(명사)를 좋아하다"처럼 표현이면 세지 않는다)
- 반복 오류: 기간 안의 오류를 교재 항목 ID(없으면 바른 표현)로 묶어 2번 이상 나온 것
- 학생에게 보낼 문장: 개수와 늘어난 양만 쓴다. "735개 중 42개" 같은 비율은 초급 학생을 꺾을 수 있어 선생님 화면에만 둔다
"""

from collections import Counter
from datetime import date

from pydantic import BaseModel, Field

from app.agent.lesson_prep.textbook import load_all_items
from app.standard.level_test import LEVEL_NAMES
from app.standard.levels import get_item, grammar_items, standard_ids, vocab_items, word_level

# ---------------------------------------------------------------------------
# 요청 (Spring이 DB에서 모아 보낸다, ADR-0005)
# ---------------------------------------------------------------------------


class ReportLesson(BaseModel):
    lesson_no: int
    date: date
    minutes: int
    unit_no: int
    covered_item_ids: list[str] = []
    strengths: list[str] = []
    errors: list[dict] = []  # post_lesson의 LessonError 모양 {student_said, correction, item_id, note}


class ReportWeakness(BaseModel):
    item_id: str | None = None
    description: str
    resolved: bool = False
    created_at: date
    resolved_at: date | None = None


class ReportStudent(BaseModel):
    name: str
    native_language: str
    standard_level: int | None = None
    target_level: int | None = None
    next_unit: int | None = None


class ReportRequest(BaseModel):
    student: ReportStudent
    date_from: date | None = Field(default=None, description="기간 시작 (없으면 첫 수업부터)")
    date_to: date
    lessons: list[ReportLesson] = Field(default=[], description="승인된 수업 기록 전체 (기간 밖 포함, 누적 계산용)")
    weaknesses: list[ReportWeakness] = []


# ---------------------------------------------------------------------------
# 계산
# ---------------------------------------------------------------------------


def _learned(lessons: list[ReportLesson]) -> tuple[dict[str, dict], dict[str, dict]]:
    """다룬 항목(단원 시트 ID, 옛 교재 ID도 받는다) → ({표준 문법 ID: 항목}, {어휘 글자: {word, level}})"""
    textbook = load_all_items()
    grammar, vocab = {}, {}
    for lesson in lessons:
        for item_id in lesson.covered_item_ids:
            # 단원 시트 문법 하나가 표준 항목 여럿을 다룰 수 있다 (-습니다/-습니까)
            for sid in textbook.get(item_id, {}).get("standard_ids") or standard_ids(item_id):
                item = get_item(sid)
                if sid.startswith("std-g-") and item:
                    grammar[sid] = item
            item = textbook.get(item_id)
            if item and item["kind"] == "vocab":
                level = word_level(item["word"], item["pos"])
                if level is not None:
                    vocab[item["word"]] = {"word": item["word"], "level": level}
    return grammar, vocab


def _error_key(error: dict) -> str:
    return error.get("item_id") or (error.get("correction") or error.get("student_said") or "").strip()


def build_report(req: ReportRequest) -> dict:
    lessons = sorted(req.lessons, key=lambda l: (l.date, l.lesson_no))
    start = req.date_from or (lessons[0].date if lessons else req.date_to)
    before = [l for l in lessons if l.date < start]
    during = [l for l in lessons if start <= l.date <= req.date_to]
    upto = before + during

    grammar_before, vocab_before = _learned(before)
    grammar_all, vocab_all = _learned(upto)
    new_grammar = [g for sid, g in grammar_all.items() if sid not in grammar_before]
    new_vocab = [v for w, v in vocab_all.items() if w not in vocab_before]

    # 등급별 범위: 1급 ~ max(지금 배울 등급, 목표 등급)
    student = req.student
    top = max(student.standard_level or 1, student.target_level or 1, 1)
    coverage = []
    for level in range(1, top + 1):
        g_total = sum(1 for g in grammar_items() if g["level"] == level)
        v_total = sum(1 for v in vocab_items() if v["level"] == level)
        coverage.append(
            {
                "level": level,
                "name": LEVEL_NAMES[level],
                "grammar": {"learned": sum(1 for g in grammar_all.values() if g["level"] == level), "total": g_total},
                "vocab": {"learned": sum(1 for v in vocab_all.values() if v["level"] == level), "total": v_total},
            }
        )

    # 목표까지 남은 문법 (지금 배울 등급부터 목표 등급까지, 표준 목록 순서)
    remaining = []
    if student.target_level:
        low = max(student.standard_level or 1, 1)
        remaining = [
            {"id": g["id"], "level": g["level"], "form": g["form"]}
            for g in grammar_items()
            if low <= g["level"] <= student.target_level and g["id"] not in grammar_all
        ]

    # 반복 오류 (기간 안)
    counter: Counter[str] = Counter()
    last: dict[str, dict] = {}
    for lesson in during:
        for error in lesson.errors:
            key = _error_key(error)
            if key:
                counter[key] += 1
                last[key] = error
    repeated = [
        {"key": key, "count": n, "student_said": last[key].get("student_said", ""), "correction": last[key].get("correction", ""), "item_id": last[key].get("item_id")}
        for key, n in counter.most_common()
        if n >= 2
    ][:3]

    strengths = list(dict.fromkeys(s for l in during for s in l.strengths))
    resolved = [w for w in req.weaknesses if w.resolved and w.resolved_at and start <= w.resolved_at <= req.date_to]
    open_weaknesses = [w for w in req.weaknesses if not w.resolved]

    report = {
        "student": student.model_dump(),
        "level_name": LEVEL_NAMES.get(student.standard_level) if student.standard_level is not None else None,
        "target_name": LEVEL_NAMES.get(student.target_level) if student.target_level else None,
        "period": {"from": start.isoformat(), "to": req.date_to.isoformat()},
        "lessons": {"count": len(during), "minutes": sum(l.minutes for l in during), "total_count": len(upto), "units": sorted({l.unit_no for l in during})},
        "new": {
            "grammar": [{"id": g["id"], "form": g["form"], "level": g["level"]} for g in new_grammar],
            "vocab": sorted(new_vocab, key=lambda v: (v["level"], v["word"])),
        },
        "total": {"grammar": len(grammar_all), "vocab": len(vocab_all)},
        "coverage": coverage,
        "remaining_to_target": {"count": len(remaining), "next": remaining[:5]},
        "strengths": strengths,
        "resolved_weaknesses": [w.description for w in resolved],
        "open_weaknesses": [w.description for w in open_weaknesses],
        "repeated_errors": repeated,
    }
    report["messages"] = {
        "ko": render_message(report, "ko"),
        student.native_language: render_message(report, student.native_language),
    }
    return report


# ---------------------------------------------------------------------------
# 학생에게 보낼 문장 (템플릿). 학습 항목(문법·단어)은 한국어 그대로 둔다.
# ---------------------------------------------------------------------------

TEXT = {
    "ko": {
        "title": "{name} 님의 한국어 학습 리포트 ({from_} ~ {to})",
        "lessons": "수업 {count}회, {minutes}분 함께 공부했어요.",
        "new": "새로 배운 것: 문법 {g}개, 단어 {v}개",
        "new_grammar": "새 문법: {forms}",
        "total": "지금까지 배운 것: 문법 {g}개, 단어 {v}개",
        "level": "지금 단계: {level}",
        "target": " (목표: {target})",
        "strengths": "잘한 점: {items}",
        "resolved": "극복한 것: {items}",
        "focus": "다음에 함께 연습할 것: {items}",
        "none": "이 기간에 기록된 수업이 없어요.",
    },
    "ja": {
        "title": "{name}さんの韓国語学習レポート（{from_}〜{to}）",
        "lessons": "レッスン{count}回、{minutes}分いっしょに勉強しました。",
        "new": "新しく学んだこと：文法{g}個、単語{v}個",
        "new_grammar": "新しい文法：{forms}",
        "total": "これまでに学んだこと：文法{g}個、単語{v}個",
        "level": "今の段階：{level}",
        "target": "（目標：{target}）",
        "strengths": "よくできたこと：{items}",
        "resolved": "克服したこと：{items}",
        "focus": "次にいっしょに練習すること：{items}",
        "none": "この期間に記録されたレッスンはありません。",
    },
    "en": {
        "title": "{name}'s Korean progress report ({from_} – {to})",
        "lessons": "We studied together in {count} lessons ({minutes} minutes).",
        "new": "New this period: {g} grammar points, {v} words",
        "new_grammar": "New grammar: {forms}",
        "total": "Learned so far: {g} grammar points, {v} words",
        "level": "Current stage: {level}",
        "target": " (goal: {target})",
        "strengths": "What you did well: {items}",
        "resolved": "What you overcame: {items}",
        "focus": "What we'll practice next: {items}",
        "none": "No lessons were recorded in this period.",
    },
}
# 등급 이름은 학생 언어로 (표준 교육과정 등급이라는 점은 선생님 화면에서 설명한다)
LEVEL_TEXT = {
    "ko": lambda n: "입문 (한글)" if n == 0 else f"{n}급",
    "ja": lambda n: "入門（ハングル）" if n == 0 else f"{n}級",
    "en": lambda n: "Beginner (Hangul)" if n == 0 else f"Level {n}",
}


def render_message(report: dict, lang: str) -> str:
    t = TEXT[lang]
    s = report["student"]
    lines = [t["title"].format(name=s["name"], from_=report["period"]["from"], to=report["period"]["to"]), ""]
    if not report["lessons"]["count"]:
        return "\n".join(lines + [t["none"]])

    lines.append(t["lessons"].format(count=report["lessons"]["count"], minutes=report["lessons"]["minutes"]))
    new = report["new"]
    lines.append(t["new"].format(g=len(new["grammar"]), v=len(new["vocab"])))
    if new["grammar"]:
        lines.append(t["new_grammar"].format(forms=", ".join(g["form"] for g in new["grammar"])))
    lines.append(t["total"].format(g=report["total"]["grammar"], v=report["total"]["vocab"]))
    if s["standard_level"] is not None:
        level = t["level"].format(level=LEVEL_TEXT[lang](s["standard_level"]))
        if s["target_level"]:
            level += t["target"].format(target=LEVEL_TEXT[lang](s["target_level"]))
        lines.append(level)
    # 잘한 점·극복한 것·다음 연습은 선생님이 쓴 한국어 기록이라 그대로 붙인다
    if report["strengths"]:
        lines.append(t["strengths"].format(items=" / ".join(report["strengths"][:3])))
    if report["resolved_weaknesses"]:
        lines.append(t["resolved"].format(items=" / ".join(report["resolved_weaknesses"][:3])))
    focus = [e["correction"] for e in report["repeated_errors"]] or report["open_weaknesses"][:3]
    if focus:
        lines.append(t["focus"].format(items=" / ".join(focus)))
    return "\n".join(lines)
