package com.koreantutor.student;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

/** 학생 API의 요청·응답 모양 (프론트와 주고받는 JSON은 camelCase) */
public final class StudentDtos {

    private StudentDtos() {
    }

    // shared/constraints.json 의 item_id_pattern 과 같다. 표준 ID(std-g-007), 교재 안 ID(ko1-u02-d01), 옛 교재 ID(u02-g01, 이전 전 기록) (기술 ADR-0032)
    public static final String ITEM_ID_PATTERN = "^(std-[gv]-\\d{3,5}|[a-z0-9]+-u\\d{2}-[vgdrex]\\d{2}|u\\d{2}-[vgdre]\\d{2})$";
    // shared/constraints.json 의 book_pattern 과 같다 (단원 시트 교재 ID: ko1, ko2)
    public static final String BOOK_PATTERN = "^[a-z0-9]{2,10}$";
    // shared/constraints.json 의 personas 와 같다
    public static final String PERSONA_PATTERN = "structured|conversation|travel|business";

    public record WeaknessDto(
            Long id,
            @Pattern(regexp = ITEM_ID_PATTERN, message = "항목 ID 형식이 아닙니다 (예: std-g-007)") String itemId,
            @NotBlank @Size(max = 500) String description,
            Boolean resolved,     // 비우면 false
            Long sinceLessonId,   // 아래 셋은 응답 전용 (요청에서는 무시)
            OffsetDateTime createdAt,
            OffsetDateTime resolvedAt) {

        public boolean isResolved() {
            return Boolean.TRUE.equals(resolved);
        }

        static WeaknessDto from(Weakness w) {
            return new WeaknessDto(w.getId(), w.getItemId(), w.getDescription(), w.isResolved(),
                    w.getSinceLessonId(), w.getCreatedAt(), w.getResolvedAt());
        }
    }

    public record StudentRequest(
            @NotBlank @Size(max = 100) String name,
            @NotNull @Pattern(regexp = "ja|en") String nativeLanguage,
            @Size(max = 200) String level,
            // 지금 배울 표준 등급은 필수다. 체험수업 레벨테스트로 정한다 (기획 ADR-0018)
            @NotNull(message = "현재 수준(표준 등급)을 골라 주세요") @Min(0) @Max(6) Integer standardLevel,
            @Min(1) @Max(6) Integer targetLevel,
            @PastOrPresent LocalDate levelAssessedOn,
            @Pattern(regexp = PERSONA_PATTERN) String persona,
            List<@NotBlank String> goals,
            List<@NotBlank String> interests,
            @Pattern(regexp = BOOK_PATTERN) String nextBook,
            @Min(1) Integer nextUnit,
            @Min(10) @Max(180) Integer lessonMinutesDefault,
            String notes,
            @Pattern(regexp = "active|paused") String status,
            List<@Valid WeaknessDto> weaknesses) {
    }

    public record StudentDetail(
            Long id, String name, String nativeLanguage, String level,
            Integer standardLevel, Integer targetLevel, LocalDate levelAssessedOn, String persona,
            List<String> goals, List<String> interests, String nextBook, int nextUnit, int lessonMinutesDefault,
            String notes, String status, List<WeaknessDto> weaknesses,
            OffsetDateTime createdAt, OffsetDateTime updatedAt) {

        static StudentDetail from(Student s) {
            return new StudentDetail(s.getId(), s.getName(), s.getNativeLanguage(), s.getLevel(),
                    s.getStandardLevel(), s.getTargetLevel(), s.getLevelAssessedOn(), s.getPersona(),
                    s.getGoals(), s.getInterests(), s.getNextBook(), s.getNextUnit(), s.getLessonMinutesDefault(),
                    s.getNotes(), s.getStatus(), s.getWeaknesses().stream().map(WeaknessDto::from).toList(),
                    s.getCreatedAt(), s.getUpdatedAt());
        }
    }

    /** 대시보드 학생 카드 (PRD F5-1) */
    public record StudentSummary(
            Long id, String name, String nativeLanguage, String level, Integer standardLevel, String persona,
            String nextBook, int nextUnit, String status,
            LocalDate lastLessonDate, List<String> mainWeaknesses) {
    }

    public record IntakeRequest(@NotBlank @Size(max = 4000) String text) {
    }
}
