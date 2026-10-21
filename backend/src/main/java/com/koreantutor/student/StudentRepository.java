package com.koreantutor.student;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface StudentRepository extends JpaRepository<Student, Long> {

    List<Student> findAllByOrderByStatusAscNameAsc();

    /** 채팅에서 이름으로 학생 찾기 (부분 일치, 대소문자 무시) */
    List<Student> findByNameContainingIgnoreCase(String name);

    Optional<Student> findFirstByNameIgnoreCase(String name);
}
