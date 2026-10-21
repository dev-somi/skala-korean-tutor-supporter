package com.koreantutor.record;

import com.koreantutor.student.StudentDtos;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public final class RecordDtos {

    private RecordDtos() {
    }

    /** noteStartedAt: 선생님이 메모를 쓰기 시작한 시각 (화면에서 보냄, 정리 시간 측정 F7-2). 없으면 지금. */
    public record RecordRequest(@NotBlank @Size(max = 30000) String rawNote, OffsetDateTime noteStartedAt) {
    }

    public record WeaknessChange(
            @NotNull @Pattern(regexp = "add|resolve") String action,
            Long weaknessId,
            @Pattern(regexp = StudentDtos.ITEM_ID_PATTERN) String itemId,
            @NotBlank @Size(max = 500) String description) {
    }

    /**
     * 선생님이 승인한 내용. 화면에서 체크를 푼 항목은 빼고 보낸다 (항목별 승인, PRD F4-4).
     * errors / homework / feedbackMessage는 AI 초안 모양 그대로(snake_case 키) 받아 보관만 한다.
     * understanding은 선생님이 확인한 항목별 이해도로, 수업(lesson.understanding)에 남아 다음 수업 복습 순서를 정한다.
     */
    public record ApproveRequest(
            @NotNull List<@Pattern(regexp = StudentDtos.ITEM_ID_PATTERN) String> coveredItemIds,
            List<String> strengths,
            List<Map<String, Object>> errors,
            List<@Valid WeaknessChange> weaknessChanges,
            List<Map<String, Object>> homework,
            String nextLessonNote,
            Map<String, Object> feedbackMessage,
            @Min(1) Integer nextUnit,
            Map<@Pattern(regexp = StudentDtos.ITEM_ID_PATTERN) String, @NotNull @Pattern(regexp = UNDERSTANDING_LEVELS) String> understanding) {
    }

    /** 항목별 이해도 값 (기술 ADR-0033). 키는 교재 항목 ID */
    public static final String UNDERSTANDING_LEVELS = "confused|shaky|ok";

    public record RecordView(Long lessonId, Long studentId, String studentName, int lessonNo, String rawNote,
                             Map<String, Object> draft, Map<String, Object> approved, OffsetDateTime approvedAt,
                             OffsetDateTime updatedAt) {

        static RecordView from(LessonRecord r) {
            var lesson = r.getLesson();
            return new RecordView(lesson.getId(), lesson.getStudent().getId(), lesson.getStudent().getName(),
                    lesson.getLessonNo(), r.getRawNote(), r.getDraft(), r.getApproved(), r.getApprovedAt(), r.getUpdatedAt());
        }
    }
}
