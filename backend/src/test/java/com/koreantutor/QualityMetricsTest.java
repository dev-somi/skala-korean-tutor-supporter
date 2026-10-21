package com.koreantutor;

import com.koreantutor.lesson.ReviewDecision;
import com.koreantutor.timelog.QualityMetrics;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** 주 지표 계산 규칙 (기획 ADR-0020). Spring·DB 없이 돈다. */
class QualityMetricsTest {

    @Test
    void onlyTheFirstDecisionPerCategoryCounts() {
        var rates = QualityMetrics.firstApproveRates(List.of(
                new ReviewDecision(1L, "review", "approve"),
                new ReviewDecision(1L, "new_vocab", "approve"),
                new ReviewDecision(1L, "new_grammar", "feedback"),
                new ReviewDecision(1L, "homework", "edit"),
                new ReviewDecision(1L, "new_grammar", "approve"),   // 다시 만든 뒤 승인: 첫 결정이 아니라 세지 않는다
                new ReviewDecision(2L, "new_grammar", "approve")));
        assertThat(rates.get("all")).isEqualTo(new QualityMetrics.Rate(5, 3, 60.0));
        assertThat(rates.get("new_grammar")).isEqualTo(new QualityMetrics.Rate(2, 1, 50.0));
        assertThat(rates.get("homework")).isEqualTo(new QualityMetrics.Rate(1, 0, 0.0));
    }

    @Test
    void noDecisionsGivesNullPercent() {
        assertThat(QualityMetrics.firstApproveRates(List.of()).get("all")).isEqualTo(new QualityMetrics.Rate(0, 0, null));
    }

    @Test
    @SuppressWarnings("unchecked")
    void keptItemsCompareDraftWithApproved() {
        Map<String, Object> error1 = Map.of("student_said", "드라마을", "correction", "드라마를", "item_id", "u03-g02", "note", "");
        Map<String, Object> error2 = Map.of("student_said", "학교에서 가요", "correction", "학교에 가요", "note", "");
        Map<String, Object> draft = Map.of(
                "covered_item_ids", List.of("u03-v01", "u03-v02", "u03-g02"),
                "strengths", List.of("-습니다 잘함", "질문을 먼저 함"),
                "errors", List.of(error1, error2),
                "weakness_changes", List.of(Map.of("action", "add", "item_id", "u03-g02", "description", "을/를")),
                "homework", List.of());
        Map<String, Object> approved = Map.of(
                "coveredItemIds", List.of("u03-v01", "u03-g02"),                    // 하나 뺌
                "strengths", List.of("-습니다를 정확히 씀", "질문을 먼저 함"),            // 하나 고침
                "errors", List.of(error1),                                           // 하나 뺌
                "weaknessChanges", List.of(Map.of("action", "add", "itemId", "u03-g02", "description", "을/를")),
                "homework", List.of());

        var rates = QualityMetrics.keptDraftItems(List.<Map<String, Object>[]>of(new Map[]{draft, approved}));
        assertThat(rates.get("covered_item_ids")).isEqualTo(new QualityMetrics.Rate(3, 2, 66.7));
        assertThat(rates.get("strengths")).isEqualTo(new QualityMetrics.Rate(2, 1, 50.0));
        assertThat(rates.get("errors")).isEqualTo(new QualityMetrics.Rate(2, 1, 50.0));
        assertThat(rates.get("weakness_changes")).isEqualTo(new QualityMetrics.Rate(1, 1, 100.0)); // snake·camel 키를 맞춰 비교
        assertThat(rates.get("all")).isEqualTo(new QualityMetrics.Rate(8, 5, 62.5));
    }
}
