package com.koreantutor.lesson;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface LessonRepository extends JpaRepository<Lesson, Long> {

    List<Lesson> findByStudentIdOrderByLessonNoDesc(Long studentId);

    List<Lesson> findByStudentIdAndStatusOrderByLessonNo(Long studentId, String status);

    @Query("select coalesce(max(l.lessonNo), 0) from Lesson l where l.student.id = :studentId")
    int maxLessonNo(Long studentId);

    /** 가장 최근에 수업한 날 (대시보드 카드의 "마지막 수업일") */
    @Query("select max(l.lessonDate) from Lesson l where l.student.id = :studentId and l.status in ('done', 'recorded')")
    Optional<java.time.LocalDate> lastLessonDate(Long studentId);

    /** 승인 대기 중인 수업안: 준비를 시작했지만 아직 확정되지 않은 수업 */
    @Query("select l from Lesson l join fetch l.student where l.status = 'planned' and l.prepThreadId is not null order by l.updatedAt desc")
    List<Lesson> findPendingPrep();

    @Query("select l from Lesson l join fetch l.student where l.status = 'prepared' and (l.lessonDate is null or l.lessonDate <= :today) order by l.lessonDate")
    List<Lesson> findToRecord(java.time.LocalDate today);
}
