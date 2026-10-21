package com.koreantutor.lesson;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReviewDecisionRepository extends JpaRepository<ReviewDecision, Long> {

    /** 수업별·시간순. 범주마다 처음 나온 줄이 첫 결정이다 */
    List<ReviewDecision> findAllByOrderByLessonIdAscIdAsc();
}
