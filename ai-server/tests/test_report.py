"""
학습자별 진도·향상 리포트 (app/standard/report.py, /report/progress) 확인. LLM을 쓰지 않는다.
교재 데이터(data/textbook, git 제외)가 있어야 배운 항목을 셀 수 있다.
"""

import pytest

from app.agent.lesson_prep.textbook import get_data_dir
from app.standard.report import ReportRequest, build_report

pytestmark = pytest.mark.skipif(
    not (get_data_dir() / "textbook" / "unit_03.json").exists(), reason="교재 데이터가 없다 (저장소에 넣지 않는 데이터)"
)

ERROR = {"student_said": "드라마을 좋아해요", "correction": "드라마를 좋아해요", "item_id": "u03-g02", "note": ""}


def request(**overrides) -> ReportRequest:
    body = {
        "student": {"name": "유이", "native_language": "ja", "standard_level": 1, "target_level": 2, "next_unit": 4},
        "date_from": "2026-10-01",
        "date_to": "2026-10-31",
        "lessons": [
            # 기간 전 수업: 2과 (누적에만 들어간다)
            {"lesson_no": 1, "date": "2026-09-20", "minutes": 50, "unit_no": 2, "covered_item_ids": ["u02-g01", "u02-v01", "u02-v02"]},
            # 기간 안 수업 2회: 3과
            {
                "lesson_no": 2, "date": "2026-10-05", "minutes": 50, "unit_no": 3,
                "covered_item_ids": ["u03-g01", "u03-g02", "u03-v01", "u03-v02", "u03-v14"],
                "strengths": ["-습니다를 정확히 씀"], "errors": [ERROR],
            },
            {
                "lesson_no": 3, "date": "2026-10-12", "minutes": 40, "unit_no": 3,
                "covered_item_ids": ["u03-g02", "u03-v03"],
                "strengths": ["-습니다를 정확히 씀", "질문을 먼저 함"], "errors": [ERROR, {"student_said": "학교에서 가요", "correction": "학교에 가요"}],
            },
        ],
        "weaknesses": [
            {"item_id": "u02-g01", "description": "이/가 구분", "resolved": True, "created_at": "2026-09-20", "resolved_at": "2026-10-12"},
            {"description": "받침 발음", "created_at": "2026-09-20"},
        ],
    }
    body.update(overrides)
    return ReportRequest.model_validate(body)


def test_period_counts_only_lessons_inside():
    report = build_report(request())
    assert report["lessons"] == {"count": 2, "minutes": 90, "total_count": 3, "units": [3]}


def test_new_vs_total_learning():
    """기간 전에 배운 것은 '새로 배운 것'에 안 들어가고 누적에만 들어간다."""
    report = build_report(request())
    new_forms = {g["form"] for g in report["new"]["grammar"]}
    assert new_forms == {"-습니다", "-습니까", "을"}  # u03-g01은 표준 항목 2개, 이/가(u02)는 기간 전
    assert {v["word"] for v in report["new"]["vocab"]} == {"노래", "드라마", "음식"}  # u03-v14는 표현이라 세지 않는다
    assert report["total"] == {"grammar": 4, "vocab": 5}


def test_coverage_against_standard_levels():
    report = build_report(request())
    level1 = report["coverage"][0]
    assert level1["grammar"] == {"learned": 4, "total": 45}
    assert level1["vocab"]["total"] == 735
    assert [c["level"] for c in report["coverage"]] == [1, 2]  # 목표 2급까지


def test_remaining_to_target_excludes_learned():
    report = build_report(request())
    assert report["remaining_to_target"]["count"] == 45 + 45 - 4
    assert "을" not in {g["form"] for g in report["remaining_to_target"]["next"]}


def test_repeated_errors_and_weakness_changes():
    report = build_report(request())
    assert report["repeated_errors"] == [
        {"key": "u03-g02", "count": 2, "student_said": "드라마을 좋아해요", "correction": "드라마를 좋아해요", "item_id": "u03-g02"}
    ]
    assert report["resolved_weaknesses"] == ["이/가 구분"]
    assert report["open_weaknesses"] == ["받침 발음"]
    assert report["strengths"] == ["-습니다를 정확히 씀", "질문을 먼저 함"]  # 중복 제거


def test_messages_show_counts_not_ratios():
    """학생에게 보낼 문장에는 '45개 중 4개' 같은 비율을 쓰지 않는다 (기획 ADR-0019)."""
    report = build_report(request())
    assert set(report["messages"]) == {"ko", "ja"}
    for text in report["messages"].values():
        assert "45" not in text and "735" not in text
    assert "문법 3개, 단어 3개" in report["messages"]["ko"]
    assert "文法3個、単語3個" in report["messages"]["ja"]
    assert "드라마를 좋아해요" in report["messages"]["ko"]  # 반복 오류가 다음 연습으로


def test_no_lessons_in_period():
    report = build_report(request(date_from="2026-11-01", date_to="2026-11-30"))
    assert report["lessons"]["count"] == 0
    assert "기록된 수업이 없어요" in report["messages"]["ko"]


def test_api(client):
    body = request().model_dump(mode="json")
    res = client.post("/report/progress", json=body)
    assert res.status_code == 200
    assert res.json()["lessons"]["count"] == 2
