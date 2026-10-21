"""
이 파일의 역할: 터미널에서 에이전트를 실행한다. 선생님 검토는 키보드 입력으로 받는다.

실행 방법:
  uv run python run.py                      # 샘플 학생, 프로필의 next_unit, 일본어, 50분
  uv run python run.py --lang en            # 영어로
  uv run python run.py --unit 3 --minutes 40

진행 상황은 output/checkpoints.db에 저장된다. 검토 도중에 프로그램을 꺼도
같은 --thread 값으로 다시 실행하면 멈춘 곳에서 이어진다.
"""

import argparse
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.agent.lesson_prep.graph import build_graph, make_initial_state
from app.agent.lesson_prep.schemas import CATEGORIES, CATEGORY_NAMES
from app.agent.lesson_prep.textbook import PROJECT_DIR


def show_review(payload: dict) -> None:
    """자동 검토 결과를 화면에 보여준다."""
    review = payload["review_result"]
    if payload["review_warning"]:
        print("\n⚠️  경고: 자동 검토를 여러 번 다시 해도 통과하지 못했습니다. 아래 문제를 직접 확인해 주세요.")
    print("\n===== 자동 검토 결과 =====")
    for check in review["checks"]:
        mark = "통과" if check["passed"] else "실패"
        print(f"[{mark}] {check['name']}: {check['reason']}")


def show_draft(category: str, draft: dict) -> None:
    """범주 하나의 초안을 화면에 보여준다."""
    print(f"\n===== {CATEGORY_NAMES[category]} ({draft['minutes']}분) =====")
    print("항목:", ", ".join(draft["item_ids"]))
    print("이유:", draft["reason"])
    print("\n[개인화 설명]")
    print(draft["explanation"])
    for example in draft["examples"]:
        mark = " (새 예문)" if example["is_new"] else ""
        print(f"  예) {example['korean']}{mark}")
    print("\n[대본]")
    print(draft["script"])


def ask_text(question: str) -> str:
    """한 줄을 입력받는다. 글 안에서 줄을 바꾸고 싶으면 \\n 이라고 쓰면 된다."""
    return input(question).strip().replace("\\n", "\n")


def ask_decisions(payload: dict) -> dict:
    """아직 승인되지 않은 범주마다 선생님의 결정을 입력받아 dict로 돌려준다."""
    decisions = {}
    for category in CATEGORIES:
        if category in payload["approved_categories"]:
            continue  # 이미 승인된 범주는 다시 묻지 않는다

        show_draft(category, payload["drafts"][category])
        choice = ""
        while choice not in ("1", "2", "3"):
            choice = input("\n1) 승인  2) 직접 수정  3) 피드백 주고 다시 생성  > ").strip()

        if choice == "1":
            decisions[category] = {"action": "approve"}
        elif choice == "2":
            decision = {"action": "edit"}
            explanation = ask_text("새 설명 (그대로 두려면 엔터): ")
            script = ask_text("새 대본 (그대로 두려면 엔터): ")
            if explanation:
                decision["explanation"] = explanation
            if script:
                decision["script"] = script
            decisions[category] = decision
        else:
            decisions[category] = {"action": "feedback", "feedback": ask_text("피드백: ")}
    return decisions


def main() -> None:
    # --- 1. 실행 옵션 읽기 ---
    parser = argparse.ArgumentParser(description="한국어 수업 자료 생성 에이전트")
    parser.add_argument("--student", default="student_sample", help="학생 프로필 파일 이름 (확장자 제외)")
    parser.add_argument("--unit", type=int, default=None, help="과 번호 (생략하면 프로필의 next_unit)")
    parser.add_argument("--lang", default="ja", choices=["ja", "en"], help="설명 언어")
    parser.add_argument("--minutes", type=int, default=50, help="수업 시간(분)")
    parser.add_argument("--thread", default="demo", help="실행 이름. 같은 이름으로 실행하면 이어서 한다")
    args = parser.parse_args()

    # --- 2. 체크포인터(진행 상황 저장소)와 그래프 준비 ---
    (PROJECT_DIR / "output").mkdir(exist_ok=True)
    connection = sqlite3.connect(PROJECT_DIR / "output" / "checkpoints.db", check_same_thread=False)
    graph = build_graph(SqliteSaver(connection))
    config = {"configurable": {"thread_id": args.thread}}

    # --- 3. 시작하거나, 멈춘 곳에서 이어가기 ---
    snapshot = graph.get_state(config)
    if snapshot.next:
        # 끝나지 않은 이전 실행이 있다 -> 입력 없이(None) 부르면 멈춘 곳에서 이어진다
        print(f"'{args.thread}' 실행을 이어서 진행합니다. (다음 단계: {snapshot.next[0]})")
        result = graph.invoke(None, config)
    else:
        print("수업안을 만드는 중입니다. 1~3분 정도 걸립니다...")
        result = graph.invoke(make_initial_state(args.student, args.unit, args.lang, args.minutes), config)

    # --- 4. 선생님 검토 반복: 그래프가 멈출 때마다 결정을 입력받아 재개한다 ---
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value  # human_review가 interrupt()에 넘긴 값
        show_review(payload)
        decisions = ask_decisions(payload)
        print("\n결정을 반영하는 중입니다...")
        result = graph.invoke(Command(resume=decisions), config)

    # --- 5. 결과 알려주기: 7단계 수업 틀 (PPT는 만들지 않는다, ADR-0015) ---
    print("\n완료! 수업 진행")
    for i, step in enumerate(result["briefing"]["lesson_frame"], 1):
        print(f"{i}. {step['name']} ({step['minutes']}분) — {step['guide']}")
        for item in step["items"]:
            print(f"   - {item}")
        for category in step["categories"]:
            print(f"   [{category}] {', '.join(result['drafts'][category]['item_ids'])}")
        if step.get("culture") is not None:
            note = result["briefing"]["culture"][step["culture"]]
            print(f"   [문화] {note['summary']} ({note['source']})\n   [비교 질문] {note['question_ko']} / {note['question_l1']}")
        elif "culture" in step:
            print("   [문화] (자료에서 못 찾음 — 선생님이 채워 주세요)")


if __name__ == "__main__":
    main()
