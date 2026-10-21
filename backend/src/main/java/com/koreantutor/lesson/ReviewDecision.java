package com.koreantutor.lesson;

import jakarta.persistence.*;

import java.time.OffsetDateTime;

/** 수업안 검토에서 선생님이 범주 하나에 내린 결정 (approve | edit | feedback). 품질 지표용 (기획 ADR-0020) */
@Entity
@Table(name = "review_decision")
public class ReviewDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long lessonId;
    private String category;
    private String action;
    private OffsetDateTime decidedAt = OffsetDateTime.now();

    protected ReviewDecision() {
    }

    public ReviewDecision(Long lessonId, String category, String action) {
        this.lessonId = lessonId;
        this.category = category;
        this.action = action;
    }

    public Long getId() { return id; }
    public Long getLessonId() { return lessonId; }
    public String getCategory() { return category; }
    public String getAction() { return action; }
    public OffsetDateTime getDecidedAt() { return decidedAt; }
}
