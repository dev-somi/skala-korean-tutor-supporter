package com.koreantutor.leveltest;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LevelTestResultRepository extends JpaRepository<LevelTestResult, Long> {

    List<LevelTestResult> findByStatusOrderByIdDesc(String status);
}
