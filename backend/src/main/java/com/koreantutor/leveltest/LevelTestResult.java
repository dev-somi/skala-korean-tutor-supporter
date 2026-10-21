package com.koreantutor.leveltest;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.Map;

/**
 * 저장한 레벨테스트 결과 (기획 ADR-0021). 추천 등급은 저장할 때 ai-server가 판정한다.
 * 학생 카드에는 선생님이 확인했을 때만 반영된다 (status pending → applied | dismissed).
 */
@Entity
@Table(name = "level_test_result")
public class LevelTestResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Boolean> answers;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> score;

    @JdbcTypeCode(SqlTypes.SMALLINT)
    private Integer suggestedLevel;

    private String note = "";
    private String status = "pending"; // pending | applied | dismissed
    private Long studentId;

    @JdbcTypeCode(SqlTypes.SMALLINT)
    private Integer appliedLevel;

    private OffsetDateTime takenAt = OffsetDateTime.now();
    private OffsetDateTime decidedAt;

    protected LevelTestResult() {
    }

    public LevelTestResult(Map<String, Boolean> answers, Map<String, Object> score, Integer suggestedLevel, String note) {
        this.answers = answers;
        this.score = score;
        this.suggestedLevel = suggestedLevel;
        this.note = note;
    }

    public void apply(Long studentId, int level) {
        this.status = "applied";
        this.studentId = studentId;
        this.appliedLevel = level;
        this.decidedAt = OffsetDateTime.now();
    }

    public void dismiss() {
        this.status = "dismissed";
        this.decidedAt = OffsetDateTime.now();
    }

    public boolean isPending() { return "pending".equals(status); }

    public Long getId() { return id; }
    public Map<String, Boolean> getAnswers() { return answers; }
    public Map<String, Object> getScore() { return score; }
    public Integer getSuggestedLevel() { return suggestedLevel; }
    public String getNote() { return note; }
    public String getStatus() { return status; }
    public Long getStudentId() { return studentId; }
    public Integer getAppliedLevel() { return appliedLevel; }
    public OffsetDateTime getTakenAt() { return takenAt; }
    public OffsetDateTime getDecidedAt() { return decidedAt; }
}
