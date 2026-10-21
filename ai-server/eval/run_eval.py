"""
수업 후 기록 추출 평가 (PRD 10장 "수업 후 기록 추출 정확도" 목표 80%)

  uv run python -m eval.run_eval                      # 전체 케이스, 추출 + 권위 게이트만 (피드백 메시지는 안 만듦)
  uv run python -m eval.run_eval --cases c01,c10      # 일부만
  uv run python -m eval.run_eval --with-feedback      # 피드백 메시지 + Validator 까지 (느리고 비쌈)
  uv run python -m eval.run_eval --only-reviewed      # 선생님이 검수한(reviewed=true) 케이스만

결과: eval/results/<시각>.md (사람이 읽는 표) 와 .json (원자료).
프롬프트·모델을 바꾸기 전후로 같은 데이터셋을 돌려 숫자로 비교한다 (참고노트 7-2).
LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY 가 .env 에 있으면 실행이 LangSmith 에도 기록된다.
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from app.agent.lesson_prep import llm  # noqa: F401  (.env 로드)
from app.agent.post_lesson import graph as post_lesson
from eval.scoring import score_case, summarize

EVAL_DIR = Path(__file__).parent


def build_state(case: dict, profiles: dict) -> dict:
    return {
        "profile": profiles[case["profile"]],
        "lesson": {**case["lesson"], "plan": case.get("plan")},
        "raw_note": case["raw_note"],
        "current_weaknesses": case["current_weaknesses"],
        "warnings": [],
        "rewrite_count": 0,
    }


def run_case(case: dict, profiles: dict, with_feedback: bool) -> dict:
    state = build_state(case, profiles)
    started = time.time()
    try:
        if with_feedback:
            state = post_lesson.build_graph().invoke(state)
        else:
            state.update(post_lesson.extract(state))
            state.update(post_lesson.gate(state))
        predicted = state["extraction"]
        error = None
    except Exception as exc:  # 한 케이스가 실패해도 나머지는 계속
        predicted, error = {"covered_item_ids": [], "weakness_changes": [], "homework": []}, f"{type(exc).__name__}: {exc}"
    score = score_case(case["id"], case["expected"], predicted)
    return {
        "id": case["id"],
        "note": case.get("note", ""),
        "reviewed": case.get("reviewed", False),
        "seconds": round(time.time() - started, 1),
        "error": error,
        "predicted": predicted,
        "warnings": state.get("warnings", []),
        "validation": state.get("validation"),
        "score": score.to_dict(),
    }, score


def to_markdown(summary: dict, results: list[dict], args) -> str:
    lines = [
        f"# 수업 후 기록 추출 평가 — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- 모델: `{os.environ.get('LLM_MODEL_QUALITY', llm.DEFAULT_MODELS['quality'])}` (추출) · 피드백 포함: {args.with_feedback}",
        f"- 케이스: {summary['cases']}개 (검수 완료 {sum(r['reviewed'] for r in results)}개)",
        "",
        "| 지표 | 값 |",
        "|---|---|",
    ]
    names = {
        "prd_extraction_accuracy": "**PRD 지표: 항목 ID·약점 변경 일치율** (목표 0.8)",
        "covered_f1": "다룬 항목 F1",
        "covered_precision": "다룬 항목 정밀도",
        "covered_recall": "다룬 항목 재현율",
        "covered_exact_rate": "다룬 항목 완전 일치 비율",
        "weakness_change_accuracy": "약점 변경 정확도",
        "homework_accuracy": "숙제 정확도",
        "case_pass_rate": "케이스 완전 통과율",
    }
    for key, name in names.items():
        lines.append(f"| {name} | {summary[key]} |")
    lines += ["", "## 케이스별", "", "| 케이스 | 통과 | 다룬 항목 (TP/FP/FN) | 약점 변경 | 숙제 | 설명 |", "|---|---|---|---|---|---|"]
    for r in results:
        s = r["score"]
        lines.append(
            f"| {r['id']} | {'✅' if s['passed'] else '❌'} | {s['covered_tp']}/{s['covered_fp']}/{s['covered_fn']} "
            f"| {'✅' if s['changes_exact'] else '❌'} | {'✅' if s['homework_exact'] else '❌'} | {r['note']} |"
        )
    failed = [r for r in results if not r["score"]["passed"]]
    if failed:
        lines += ["", "## 틀린 케이스 자세히", ""]
        for r in failed:
            s, p = r["score"], r["predicted"]
            lines.append(f"### {r['id']} — {r['note']}")
            if r["error"]:
                lines.append(f"- 오류: `{r['error']}`")
            lines.append(f"- 예측한 다룬 항목: {p.get('covered_item_ids')}")
            if s["changes_missed"]:
                lines.append(f"- 놓친 약점 변경: {json.dumps(s['changes_missed'], ensure_ascii=False)}")
            if s["changes_extra"]:
                lines.append(f"- 기대에 없는 약점 변경: {json.dumps(s['changes_extra'], ensure_ascii=False)}")
            if not s["homework_exact"]:
                lines.append(f"- 예측한 숙제: {json.dumps(p.get('homework'), ensure_ascii=False)}")
            if r["warnings"]:
                lines.append(f"- 게이트 경고: {r['warnings']}")
            lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="수업 후 기록 추출 평가")
    parser.add_argument("--cases", help="쉼표로 구분한 케이스 ID (기본: 전체)")
    parser.add_argument("--with-feedback", action="store_true", help="피드백 메시지와 Validator까지 실행")
    parser.add_argument("--only-reviewed", action="store_true", help="reviewed=true 케이스만")
    parser.add_argument("--workers", type=int, default=4, help="동시에 실행할 케이스 수")
    args = parser.parse_args()

    data = json.loads((EVAL_DIR / "dataset.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if args.only_reviewed:
        cases = [c for c in cases if c.get("reviewed")]
    if not cases:
        raise SystemExit("실행할 케이스가 없습니다")
    if not all(c.get("reviewed") for c in cases):
        print("주의: 검수하지 않은(reviewed=false) 케이스가 섞여 있습니다. 기대값을 확인한 뒤 true로 바꾸세요.")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outputs = list(pool.map(lambda c: run_case(c, data["profiles"], args.with_feedback), cases))
    results = [r for r, _ in outputs]
    summary = summarize([s for _, s in outputs])

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = EVAL_DIR / "results"
    out.mkdir(exist_ok=True)
    (out / f"{stamp}.json").write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / f"{stamp}.md").write_text(to_markdown(summary, results, args), encoding="utf-8")

    for r in results:
        print(f"{r['id']}: {'PASS' if r['score']['passed'] else 'FAIL'} ({r['seconds']}s){'  ' + r['error'] if r['error'] else ''}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"결과: {out / stamp}.md")


if __name__ == "__main__":
    main()
