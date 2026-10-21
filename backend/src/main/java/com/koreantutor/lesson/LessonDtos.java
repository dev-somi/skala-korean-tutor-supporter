package com.koreantutor.lesson;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public final class LessonDtos {

    private LessonDtos() {
    }

    /** 비워 두면 학생 프로필의 기본값(다음 과, 기본 수업 시간, 모국어)을 쓴다 */
    public record CreateLessonRequest(
            @Min(1) Integer unitNo,
            @Min(10) @Max(180) Integer minutes,
            @Pattern(regexp = "ja|en") String targetLang,
            LocalDate lessonDate) {
    }

    /** 범주 하나에 대한 선생님 결정 (ai-server CategoryDecision 과 같은 모양) */
    public record CategoryDecision(
            @NotNull @Pattern(regexp = "approve|edit|feedback") String action,
            String explanation,
            String script,
            String feedback) {
    }

    public record PrepReviewRequest(@NotEmpty Map<
            @Pattern(regexp = "review|new_vocab|new_grammar|homework") String,
            @Valid @NotNull CategoryDecision> decisions) {
    }

    /** plan / briefing / drafts 안의 키는 ai-server가 만든 그대로(snake_case)다 */
    public record LessonView(
            Long id, Long studentId, String studentName, int lessonNo, LocalDate lessonDate,
            int minutes, int unitNo, String targetLang, String status, String prepThreadId,
            Map<String, Object> plan, Map<String, Object> briefing, Map<String, Object> drafts,
            List<String> coveredItemIds, String pptxFile, String pdfFile,
            OffsetDateTime createdAt, OffsetDateTime updatedAt) {

        static LessonView from(Lesson l) {
            return new LessonView(l.getId(), l.getStudent().getId(), l.getStudent().getName(), l.getLessonNo(),
                    l.getLessonDate(), l.getMinutes(), l.getUnitNo(), l.getTargetLang(), l.getStatus(),
                    l.getPrepThreadId(), l.getPlan(), l.getBriefing(), l.getDrafts(), l.getCoveredItemIds(),
                    l.getPptxFile(), l.getPdfFile(), l.getCreatedAt(), l.getUpdatedAt());
        }
    }
}
