"""
이 파일의 역할: 체험수업 레벨테스트 (기획 ADR-0018, 기술 ADR-0017).

- load_level_test(): data/standard/level_test.json을 읽고, 문항마다 표준 항목(글자·길잡이말·등급)을 채우고 검사한다.
  문항 ID는 코드가 붙인다 (hangul-1, L1-g1, L1-v1 …). 화면은 이 ID로 맞음/틀림을 보낸다.
- score(answers): 맞음/틀림 → 추천 등급. 판정 규칙은 코드에 있다. LLM을 쓰지 않는다.

등급의 뜻: "지금 배울 등급"이다. 0 = 입문(한글부터), 1~6 = 표준 N급.
"""

import json
from functools import lru_cache

from pydantic import BaseModel

from app.agent.lesson_prep.textbook import get_data_dir
from app.standard.levels import get_item

LEVEL_NAMES = {0: "입문 (한글부터)", **{n: f"표준 {n}급" for n in range(1, 7)}}


@lru_cache
def load_level_test() -> dict:
    """문항을 표준 항목으로 채워서 돌려준다. ID가 없거나 등급이 맞지 않으면 에러 (데이터를 고칠 일이다)."""
    raw = json.loads((get_data_dir() / "standard" / "level_test.json").read_text(encoding="utf-8"))

    def standard(std_id: str, level: int) -> dict:
        item = get_item(std_id)
        if item is None:
            raise ValueError(f"레벨테스트 문항의 표준 ID가 없다: {std_id}")
        if item["level"] != level:
            raise ValueError(f"{std_id}는 {item['level']}급인데 {level}급 문항에 들어 있다")
        return item

    def vocab(key: str, std_id: str, level: int) -> dict:
        item = standard(std_id, level)
        return {"id": key, "std_id": std_id, "word": item["word"], "guide": item["guide"], "pos": item["pos"]}

    hangul = raw["hangul"]
    levels = []
    for section in raw["levels"]:
        n = section["level"]
        grammar = []
        for i, g in enumerate(section["grammar"], 1):
            item = standard(g["std_id"], n)
            grammar.append({"id": f"L{n}-g{i}", "form": item["form"], **g})
        levels.append(
            {
                "level": n,
                "name": LEVEL_NAMES[n],
                "minutes": section["minutes"],
                "grammar": grammar,
                "vocab": [vocab(f"L{n}-v{i}", sid, n) for i, sid in enumerate(section["vocab"], 1)],
            }
        )

    return {
        "minutes": raw["minutes"],
        "pass_ratio": raw["pass_ratio"],
        "min_answered": raw["min_answered"],
        "how_to": raw["how_to"],
        "review_note": raw["_검수"],
        "hangul": {
            "instruction": hangul["instruction"],
            "pass_min": hangul["pass_min"],
            "words": [vocab(f"hangul-{i}", sid, 1) for i, sid in enumerate(hangul["words"], 1)],
        },
        "levels": levels,
    }


class LevelResult(BaseModel):
    level: int
    answered: int
    correct: int
    status: str  # "passed" | "failed" | "not_enough" (확인한 문항이 min_answered보다 적음) | "untested"


class ScoreResult(BaseModel):
    suggested_level: int | None  # None = 판정할 만큼 보지 않았다
    suggested_name: str | None
    reason: str
    hangul_correct: int | None
    levels: list[LevelResult]


def score(answers: dict[str, bool]) -> ScoreResult:
    """
    answers: {문항 ID: 맞으면 true, 틀리면 false}. 확인하지 않은 문항은 넣지 않는다.

    1) 한글을 확인했고 pass_min보다 적게 읽었으면 → 0 (입문)
    2) 등급마다: 확인한 문항이 min_answered 이상이고 맞힌 비율이 pass_ratio 이상이면 통과
    3) 처음으로 통과 못 한 등급(틀림)이 추천 등급이다
    4) 틀린 등급이 없으면 마지막으로 통과한 등급 + 1 (6급이 끝)
    """
    test = load_level_test()
    hangul_ids = [w["id"] for w in test["hangul"]["words"]]
    hangul_seen = [answers[i] for i in hangul_ids if i in answers]
    hangul_correct = sum(hangul_seen) if hangul_seen else None

    results = []
    for section in test["levels"]:
        ids = [g["id"] for g in section["grammar"]] + [v["id"] for v in section["vocab"]]
        seen = [answers[i] for i in ids if i in answers]
        correct = sum(seen)
        if not seen:
            status = "untested"
        elif len(seen) < test["min_answered"]:
            status = "not_enough"
        elif correct / len(seen) >= test["pass_ratio"]:
            status = "passed"
        else:
            status = "failed"
        results.append(LevelResult(level=section["level"], answered=len(seen), correct=correct, status=status))

    def done(level: int | None, reason: str) -> ScoreResult:
        name = LEVEL_NAMES[level] if level is not None else None
        return ScoreResult(suggested_level=level, suggested_name=name, reason=reason, hangul_correct=hangul_correct, levels=results)

    if hangul_correct is not None and hangul_correct < test["hangul"]["pass_min"]:
        return done(0, f"한글 읽기 {hangul_correct}/{len(hangul_ids)}개 — 한글부터 시작한다")

    failed = [r for r in results if r.status == "failed"]
    passed = [r for r in results if r.status == "passed"]
    if failed:
        first = failed[0]
        return done(first.level, f"{first.level}급 {first.correct}/{first.answered}개 — 이 등급을 배울 차례다")
    if passed:
        top = passed[-1].level
        if top == 6:
            return done(6, "6급까지 통과했다")
        return done(top + 1, f"{top}급까지 통과했고 {top + 1}급은 충분히 확인하지 못했다 — 첫 수업에서 {top + 1}급 내용으로 다시 확인한다")
    if hangul_correct is not None:
        return done(1, "한글은 읽는다. 1급 문항은 충분히 확인하지 못했다")
    return done(None, f"판정하려면 한 등급에서 {test['min_answered']}문항 이상 확인해야 한다")
