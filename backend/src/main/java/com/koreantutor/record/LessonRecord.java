package com.koreantutor.record;

import com.koreantutor.common.BaseTimeEntity;
import com.koreantutor.lesson.Lesson;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.Map;

/**
 * 수업 후 기록 (Lesson 1:1). draft = AI 초안(ai-server가 만든 그대로, snake_case),
 * approved = 선생님이 승인한 내용. approved_at이 null이면 "미처리 기록"이다 (PRD F4-4).
 */
@Entity
@Table(name = "lesson_record")
public class LessonRecord extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lesson_id")
    private Lesson lesson;

    private String rawNote;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> draft;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> approved;

    private OffsetDateTime approvedAt;

    protected LessonRecord() {
    }

    public LessonRecord(Lesson lesson) {
        this.lesson = lesson;
    }

    public void saveDraft(String rawNote, Map<String, Object> draft) {
        this.rawNote = rawNote;
        this.draft = draft;
        this.approved = null;
        this.approvedAt = null;
    }

    public void approve(Map<String, Object> approved) {
        this.approved = approved;
        this.approvedAt = OffsetDateTime.now();
    }

    public boolean isApproved() { return approvedAt != null; }
    public Long getId() { return id; }
    public Lesson getLesson() { return lesson; }
    public String getRawNote() { return rawNote; }
    public Map<String, Object> getDraft() { return draft; }
    public Map<String, Object> getApproved() { return approved; }
    public OffsetDateTime getApprovedAt() { return approvedAt; }
}
