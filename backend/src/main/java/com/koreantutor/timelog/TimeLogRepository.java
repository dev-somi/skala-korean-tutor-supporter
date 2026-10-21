package com.koreantutor.timelog;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface TimeLogRepository extends JpaRepository<TimeLog, Long> {

    Optional<TimeLog> findFirstByLessonIdAndKindAndFinishedAtIsNullOrderByIdDesc(Long lessonId, String kind);

    List<TimeLog> findByKindAndFinishedAtIsNotNullOrderByStartedAtDesc(String kind);
}
