package com.koreantutor.record;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface LessonRecordRepository extends JpaRepository<LessonRecord, Long> {

    Optional<LessonRecord> findByLessonId(Long lessonId);

    /** 미처리 기록: AI 초안은 있는데 아직 승인하지 않은 것 (대시보드 할 일) */
    @Query("select r from LessonRecord r join fetch r.lesson l join fetch l.student where r.approvedAt is null order by r.updatedAt desc")
    List<LessonRecord> findPending();

    /** 학생의 승인된 기록 전체 (진도 리포트, 기획 ADR-0019) */
    @Query("select r from LessonRecord r join fetch r.lesson l where l.student.id = :studentId and r.approvedAt is not null order by l.lessonNo")
    List<LessonRecord> findApprovedByStudent(Long studentId);
}
