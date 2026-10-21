package com.koreantutor.timelog;

import jakarta.persistence.*;

import java.time.OffsetDateTime;

/** AI 없이 했을 때 걸리는 시간 (선생님이 직접 입력, PRD F7-4) */
@Entity
@Table(name = "baseline")
public class Baseline {

    @Id
    private String kind; // prep | post

    private int minutes;
    private String note = "";
    private boolean isEstimate;
    private OffsetDateTime updatedAt;

    protected Baseline() {
    }

    public Baseline(String kind) {
        this.kind = kind;
    }

    public void update(int minutes, String note, boolean isEstimate) {
        this.minutes = minutes;
        this.note = note == null ? "" : note;
        this.isEstimate = isEstimate;
        this.updatedAt = OffsetDateTime.now();
    }

    public String getKind() { return kind; }
    public int getMinutes() { return minutes; }
    public String getNote() { return note; }
    public boolean isEstimate() { return isEstimate; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
}
