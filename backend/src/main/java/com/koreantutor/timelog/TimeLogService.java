package com.koreantutor.timelog;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.OffsetDateTime;

/** 수업 준비·수업 후 정리 시간을 자동으로 잰다 (PRD F7-1, F7-2, F7-3). */
@Service
public class TimeLogService {

    private final TimeLogRepository repository;

    public TimeLogService(TimeLogRepository repository) {
        this.repository = repository;
    }

    /** 열린 세션이 있으면 그대로 쓰고, 없으면 새로 시작한다. (다시 시도해도 시작 시각이 바뀌지 않게) */
    @Transactional
    public TimeLog startIfAbsent(Long studentId, Long lessonId, String kind) {
        return startIfAbsent(studentId, lessonId, kind, null);
    }

    /** startedAt: 화면에서 잰 실제 시작 시각 (예: 메모를 쓰기 시작한 때). 미래이거나 없으면 지금. */
    @Transactional
    public TimeLog startIfAbsent(Long studentId, Long lessonId, String kind, OffsetDateTime startedAt) {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime start = startedAt == null || startedAt.isAfter(now) ? now : startedAt;
        return repository.findFirstByLessonIdAndKindAndFinishedAtIsNullOrderByIdDesc(lessonId, kind)
                .orElseGet(() -> repository.save(new TimeLog(studentId, lessonId, kind, start)));
    }

    @Transactional
    public void addAiWait(Long lessonId, String kind, Duration duration) {
        repository.findFirstByLessonIdAndKindAndFinishedAtIsNullOrderByIdDesc(lessonId, kind)
                .ifPresent(log -> log.addAiWait(duration));
    }

    @Transactional
    public void finish(Long lessonId, String kind) {
        repository.findFirstByLessonIdAndKindAndFinishedAtIsNullOrderByIdDesc(lessonId, kind)
                .ifPresent(TimeLog::finish);
    }
}
