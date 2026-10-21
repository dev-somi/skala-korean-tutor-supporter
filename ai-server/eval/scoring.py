"""
이 파일의 역할: 수업 후 기록 추출 결과를 기대값과 비교해 점수를 매긴다 (휴리스틱 채점, 참고노트 7-3).

  다룬 항목:   교재 ID 집합의 정밀도·재현율. optional_covered_item_ids 는 맞혀도 틀려도 감점 없음
  약점 변경:   resolve 는 weakness_id 가 같아야, add 는 item_id 가 같거나 설명에 키워드가 있어야 일치.
              기대에 없는 변경을 만들면 감점(오탐)
  숙제:        교재 ID 집합이 정확히 같아야 일치
  케이스 통과: 세 가지가 모두 정확히 맞을 때
"""

from dataclasses import asdict, dataclass, field


@dataclass
class CaseScore:
    case_id: str
    covered_tp: int
    covered_fp: int
    covered_fn: int
    covered_exact: bool
    changes_exact: bool
    changes_missed: list = field(default_factory=list)
    changes_extra: list = field(default_factory=list)
    homework_exact: bool = True
    passed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def change_matches(expected: dict, predicted: dict) -> bool:
    if expected["action"] != predicted.get("action"):
        return False
    if expected["action"] == "resolve":
        return expected["weakness_id"] == predicted.get("weakness_id")
    if expected.get("item_id") and expected["item_id"] == predicted.get("item_id"):
        return True
    description = predicted.get("description") or ""
    return any(k in description for k in expected.get("keywords", []))


def score_case(case_id: str, expected: dict, predicted: dict) -> CaseScore:
    exp_cov = set(expected["covered_item_ids"])
    optional = set(expected.get("optional_covered_item_ids", []))
    pred_cov = set(predicted.get("covered_item_ids", []))
    tp = len(exp_cov & pred_cov)
    fp = len(pred_cov - exp_cov - optional)
    fn = len(exp_cov - pred_cov)

    # 기대 변경 하나에 예측 변경 하나씩 짝짓는다
    remaining = list(predicted.get("weakness_changes", []))
    missed = []
    for exp in expected["weakness_changes"]:
        hit = next((p for p in remaining if change_matches(exp, p)), None)
        if hit is None:
            missed.append(exp)
        else:
            remaining.remove(hit)
    changes_exact = not missed and not remaining

    exp_hw = set(expected["homework_item_ids"])
    pred_hw = {h.get("item_id") for h in predicted.get("homework", []) if h.get("item_id")}
    homework_exact = exp_hw == pred_hw

    covered_exact = fp == 0 and fn == 0
    return CaseScore(
        case_id=case_id,
        covered_tp=tp,
        covered_fp=fp,
        covered_fn=fn,
        covered_exact=covered_exact,
        changes_exact=changes_exact,
        changes_missed=missed,
        changes_extra=remaining,
        homework_exact=homework_exact,
        passed=covered_exact and changes_exact and homework_exact,
    )


def summarize(scores: list[CaseScore]) -> dict:
    n = len(scores) or 1
    tp = sum(s.covered_tp for s in scores)
    fp = sum(s.covered_fp for s in scores)
    fn = sum(s.covered_fn for s in scores)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "cases": len(scores),
        "covered_precision": round(precision, 3),
        "covered_recall": round(recall, 3),
        "covered_f1": round(f1, 3),
        "covered_exact_rate": round(sum(s.covered_exact for s in scores) / n, 3),
        "weakness_change_accuracy": round(sum(s.changes_exact for s in scores) / n, 3),
        "homework_accuracy": round(sum(s.homework_exact for s in scores) / n, 3),
        "case_pass_rate": round(sum(s.passed for s in scores) / n, 3),
        # PRD 10장 지표: 항목 ID·약점 변경 일치율 (다룬 항목 F1 과 약점 변경 정확도의 평균), 목표 0.8
        "prd_extraction_accuracy": round((f1 + sum(s.changes_exact for s in scores) / n) / 2, 3),
    }
