package com.koreantutor.timelog;

import jakarta.persistence.*;

import java.time.Duration;
import java.time.OffsetDateTime;

/** 수업 준비(prep) / 수업 후 정리(post) 세션 하나의 시간 기록 (PRD F7) */
@Entity
@Table(name = "time_log")
public class TimeLog {

    public static final String PREP = "prep";
    public static final String POST = "post";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long studentId;
    private Long lessonId;
    private String kind;
    private OffsetDateTime startedAt;
    private OffsetDateTime finishedAt;
    private int aiWaitSeconds;
    private Integer teacherSeconds;

    protected TimeLog() {
    }

    public TimeLog(Long studentId, Long lessonId, String kind) {
        this(studentId, lessonId, kind, OffsetDateTime.now());
    }

    public TimeLog(Long studentId, Long lessonId, String kind, OffsetDateTime startedAt) {
        this.studentId = studentId;
        this.lessonId = lessonId;
        this.kind = kind;
        this.startedAt = startedAt;
    }

    public void addAiWait(Duration duration) {
        aiWaitSeconds += (int) duration.toSeconds();
    }

    /** 끝낸다. 선생님 작업 시간 = 전체 시간 - AI 대기 시간 */
    public void finish() {
        finishedAt = OffsetDateTime.now();
        long total = Duration.between(startedAt, finishedAt).toSeconds();
        teacherSeconds = (int) Math.max(0, total - aiWaitSeconds);
    }

    public boolean isOpen() { return finishedAt == null; }
    public Long getId() { return id; }
    public Long getStudentId() { return studentId; }
    public Long getLessonId() { return lessonId; }
    public String getKind() { return kind; }
    public OffsetDateTime getStartedAt() { return startedAt; }
    public OffsetDateTime getFinishedAt() { return finishedAt; }
    public int getAiWaitSeconds() { return aiWaitSeconds; }
    public Integer getTeacherSeconds() { return teacherSeconds; }
}
