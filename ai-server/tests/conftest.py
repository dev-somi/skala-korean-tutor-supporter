"""
이 파일의 역할: 테스트들이 함께 쓰는 준비물(fixture)을 모아 둔다.

핵심은 "가짜 LLM"이다. 실제 API를 부르지 않고 정해진 답을 돌려주므로,
돈과 시간을 쓰지 않고 그래프의 분기가 맞게 동작하는지 확인할 수 있다.
"""

import pytest
from pydantic import BaseModel
from fastapi.testclient import TestClient

from app.agent.lesson_prep import llm, nodes, pptx_builder, render

# 가짜 LLM이 돌려줄 선생님 브리핑
FAKE_BRIEFING = {
    "warmup_questions": ["주말에 뭐 했어요?"],
    "practice_activity": "좋아하는 드라마를 소개하는 말하기",
    "grammar_points": [{"item_id": "std-g-030", "key_points": ["받침 유무에 따라 형태가 바뀐다"]}],
    "common_mistakes": ["を와 을/를을 그대로 대응시킨다"],
    "expected_qa": [{"question": "언제 습니다를 써요?", "answer": "격식 있는 자리에서 씁니다."}],
    "tips": ["드라마 장면으로 예문을 만든다"],
}


# 가짜 LLM이 돌려줄 학생 등록 초안. 일부러 틀린 값(없는 교재 ID, 지원하지 않는 언어 등)을 섞어 둔다.
FAKE_INTAKE = {
    "name": "유이",
    "native_language": "ja",
    "level": "초급 1",
    "goals": ["서울 여행"],
    "interests": ["드라마"],
    "weaknesses": [
        {"item_id": None, "description": "받침 발음"},
        {"item_id": "std-g-001", "description": "-이에요/예요"},
        {"item_id": "std-g-999", "description": "없는 항목"},
    ],
    "next_unit": 3,
    "lesson_minutes_default": None,
    "notes": "",
    "standard_level": 1,
    "target_level": None,
    "persona": "travel",
}


# 가짜 LLM이 돌려줄 수업 후 기록. 권위 게이트가 고쳐야 할 값을 일부러 섞어 둔다.
FAKE_EXTRACTION = {
    "covered_item_ids": ["std-v-00136", "std-v-00185", "std-v-00136", "std-v-99999"],
    "strengths": ["-습니다를 잘 씀"],
    "errors": [{"student_said": "밥를 먹습니다", "correction": "밥을 먹습니다", "item_id": "std-g-007", "note": ""}],
    "weakness_changes": [
        {"action": "add", "weakness_id": None, "item_id": "std-g-007", "description": "을/를 받침 구분"},
        {"action": "add", "weakness_id": None, "item_id": None, "description": "받침 발음"},  # 이미 있음
        {"action": "resolve", "weakness_id": None, "item_id": "std-g-001", "description": "이/가"},  # id 없이 ID로 찾기
        {"action": "resolve", "weakness_id": 999, "item_id": None, "description": "없는 약점"},
    ],
    "homework": [{"item_id": "ko1-u03-e02", "description": "연습문제 2번"}],
    "next_lesson_note": "을/를 복습",
}


# 가짜 LLM이 돌려줄 학생 반응 장면. 판정(judge)이 버려야 할 장면을 일부러 섞어 둔다.
FAKE_EPISODES = [
    {"item_id": "std-v-00136", "kind": "error", "quote": "밥를 이라고 함"},
    {"item_id": "std-v-00136", "kind": "asked_again", "quote": "메모에 없는 문장"},  # 원문에 없음
    {"item_id": "std-g-007", "kind": "error", "quote": "밥를 이라고 함"},  # 다룬 항목이 아님
    {"item_id": "std-v-00185", "kind": "correct", "quote": "3과 1~2   단어 함"},  # 공백만 다름
]


# 가짜 문화 후보 (세종한국문화 1에서 찾았다고 가정)
FAKE_CULTURE = [
    {"book": "culture1", "source": "세종한국문화 1 1과 「문화」 22~23쪽", "excerpt": "음악 방송에서는 매주 인기 있는 노래를 소개해요."},
    {"book": "ko1_guide", "source": "지침서 3과 「문법 1」 36~37쪽", "excerpt": "문법 형태를 판서하고 연습시킨다."},
]


def fake_slides(homework_pages: str) -> dict:
    """가짜 write_slides 결과: 15장 모두 채우고, 어휘 슬라이드는 단어 3개."""
    note = {"goal": "목표", "procedure": "교사가 먼저 시범을 보인다.", "qa": [], "if_struggle": "선택지를 준다.", "if_good": "힌트를 없앤다.", "source": ""}
    slides = [
        {
            "no": no,
            "student_screen": [] if no == 14 else (["김치 — 김치를 좋아합니다.", "커피 — 커피를 마십니다.", "노래 — 노래가 좋습니다."] if no in (4, 5) else [f"{no}번 화면"]),
            "activity": f"{no}번 활동",
            "note": note,
            "needs_check": [],
        }
        for no in range(1, 16)
    ]
    return {
        "lesson_goal": "좋아하는 것을 두 문장으로 말할 수 있다.",
        "final_mission": "선생님과 둘 다 좋아하는 것을 하나 찾는다.",
        "slides": slides,
        "homework": {"pages": homework_pages, "items": "1~2번" if homework_pages else "", "how": "문장을 소리 내어 읽고 쓴다.", "example": "저는 김치를 좋아합니다."},
        "needs_check": [] if homework_pages else ["숙제 쪽수 확인 필요"],
    }


def fake_slide_script(no: int) -> dict:
    """가짜 write_slide_script 결과: 선생님 발화 + 학생 예상 답."""
    return {
        "lines": [
            {"who": "teacher", "ko": f"{no}번입니다. 무엇을 좋아합니까?", "hint": "", "wait": True},
            {"who": "student_expected", "ko": "비빔밥을 좋아합니다.", "hint": "", "wait": False},
        ],
        "transition": "다음 장으로 갈게요.",
        "fallback": [{"who": "teacher", "ko": "음식을 골라 보세요.", "hint": "", "wait": False}],
        "needs_check": [],
    }


class FakeLLM:
    """llm.call_llm 대신 쓰는 가짜. 어떤 프롬프트로 몇 번 불렸는지 기록한다."""

    def __init__(self):
        self.calls = []  # (프롬프트 이름, 넣은 값) 기록
        self.review_fail_times = 0  # 자동 검토를 처음 몇 번 실패시킬지
        self.counter = 0  # 생성할 때마다 다른 글이 나오도록 붙이는 번호
        self.tiers = []  # (프롬프트 이름, 모델 티어) 기록
        self.validator_fail_times = 0  # 피드백 Validator를 처음 몇 번 불합격시킬지
        self.failing_slides = set()  # 대본 생성을 실패시킬 슬라이드 번호
        self.homework_pages = "p.40"  # 가짜 슬라이드 구성안의 숙제 쪽수 ("" 이면 확인 필요로 표시)

    def count(self, prompt_name: str) -> int:
        """해당 프롬프트가 몇 번 불렸는지 센다."""
        return len([name for name, _ in self.calls if name == prompt_name])

    def __call__(self, prompt_name: str, output_schema, values: dict, tier: str = "quality") -> dict:
        # 실제 call_llm과 같은 모양으로 불렸는지 확인한다 (스키마는 pydantic 클래스, 값은 dict, 프롬프트 파일이 있음)
        assert isinstance(output_schema, type) and issubclass(output_schema, BaseModel), prompt_name
        assert isinstance(values, dict), prompt_name
        assert (llm.PROMPT_DIR / f"{prompt_name}.md").exists(), prompt_name
        self.calls.append((prompt_name, values))
        self.tiers.append((prompt_name, tier))

        if prompt_name == "briefing_grammar":
            return {"grammar_points": FAKE_BRIEFING["grammar_points"]}
        if prompt_name == "briefing_learner":
            return {k: FAKE_BRIEFING[k] for k in ("common_mistakes", "expected_qa")}
        if prompt_name == "briefing_culture":
            return {"notes": [
                {"index": 1, "summary": "음악 방송에서 팬들이 노래를 함께 따라 불러요.", "question_ko": "일본에서도 같이 불러요?", "question_l1": "日本でも一緒に歌いますか？"},
                {"index": 2, "summary": "", "question_ko": "", "question_l1": ""},  # 문화가 아닌 후보
            ]}
        if prompt_name == "briefing_personal":
            return {k: FAKE_BRIEFING[k] for k in ("warmup_questions", "practice_activity", "tips")}

        if prompt_name == "write_slides":
            return fake_slides(self.homework_pages)

        if prompt_name == "write_slide_script":
            if values["slide_no"] in self.failing_slides:
                raise RuntimeError("가짜 대본 생성 실패")
            return fake_slide_script(values["slide_no"])

        if prompt_name == "student_intake":
            return FAKE_INTAKE

        if prompt_name == "extract_record":
            return FAKE_EXTRACTION

        if prompt_name == "observe_understanding":
            return {"episodes": FAKE_EPISODES}

        if prompt_name == "write_feedback":
            self.counter += 1
            return {"target_lang_text": f"今日はよくできました{self.counter}", "korean_text": f"오늘 잘했어요{self.counter}"}

        if prompt_name == "validate_feedback":
            passed = self.count("validate_feedback") > self.validator_fail_times
            return {"is_acceptable": passed, "reasoning": "숙제가 빠졌습니다" if not passed else "좋습니다"}

        if prompt_name == "write_explanation":
            self.counter += 1
            return {
                "explanation": f"説明{self.counter}です。",
                "examples": [{"korean": "노래가 좋습니다.", "is_new": False}],
            }

        if prompt_name == "write_script":
            self.counter += 1
            return {"script": f"台本{self.counter}です。"}

        # 남은 것은 auto_review. 정해진 횟수만큼만 실패시킨다.
        passed = self.count("auto_review") > self.review_fail_times
        return {"checks": [{"name": "자연스러움", "passed": passed, "reason": "가짜 검토 결과"}]}


@pytest.fixture
def fake_llm(monkeypatch, tmp_path):
    """가짜 LLM을 끼우고, PPT는 임시 폴더에 저장되게 하고, PDF 변환은 끈다(빠르게 하려고)."""
    fake = FakeLLM()
    monkeypatch.setattr(llm, "call_llm", fake)
    # 문화 후보 검색은 임베딩 서버를 부르므로 정해진 후보로 바꾼다
    monkeypatch.setattr(nodes, "collect_culture", lambda unit: FAKE_CULTURE)
    monkeypatch.setattr(pptx_builder, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(render, "find_soffice", lambda: None)
    return fake


@pytest.fixture
def client(fake_llm, monkeypatch):
    """가짜 LLM을 쓰는 ai-server 테스트 클라이언트"""
    monkeypatch.setenv("CHECKPOINT_DB", ":memory:")
    from app.main import app

    with TestClient(app) as c:
        yield c
