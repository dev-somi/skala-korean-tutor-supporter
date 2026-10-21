package com.koreantutor.chat;

/**
 * 라우팅 게이트(저가 모델)의 구조화 출력 (PRD F6-1).
 * intent: lookup | student_upsert | lesson_prep | post_lesson | grammar_qa | general (shared/constraints.json chat_intent)
 */
public record RouteDecision(String intent, String studentName, Integer minutes, String reason) {

    public static final String LOOKUP = "lookup";
    public static final String STUDENT_UPSERT = "student_upsert";
    public static final String LESSON_PREP = "lesson_prep";
    public static final String POST_LESSON = "post_lesson";
    public static final String GRAMMAR_QA = "grammar_qa";
    public static final String GENERAL = "general";

    public RouteDecision withIntent(String newIntent, String newReason) {
        return new RouteDecision(newIntent, studentName, minutes, newReason);
    }
}
