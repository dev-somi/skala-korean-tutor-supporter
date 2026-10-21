package com.koreantutor.student;

import jakarta.persistence.*;

import java.time.OffsetDateTime;

@Entity
@Table(name = "weakness")
public class Weakness {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "student_id")
    private Student student;

    private String itemId;          // 교재 항목 ID (없으면 null)
    private String description;     // 자유 서술
    private Long sinceLessonId;
    private boolean resolved;
    private OffsetDateTime createdAt = OffsetDateTime.now();
    private OffsetDateTime resolvedAt;

    protected Weakness() {
    }

    public Weakness(String itemId, String description, Long sinceLessonId) {
        this.itemId = itemId;
        this.description = description;
        this.sinceLessonId = sinceLessonId;
    }

    public void resolve() {
        if (!resolved) {
            resolved = true;
            resolvedAt = OffsetDateTime.now();
        }
    }

    public void reopen() {
        resolved = false;
        resolvedAt = null;
    }

    public Long getId() { return id; }
    void setStudent(Student student) { this.student = student; }
    public String getItemId() { return itemId; }
    public void setItemId(String itemId) { this.itemId = itemId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Long getSinceLessonId() { return sinceLessonId; }
    public boolean isResolved() { return resolved; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public OffsetDateTime getResolvedAt() { return resolvedAt; }
}
