package com.koreantutor.dashboard;

import com.koreantutor.leveltest.LevelTestResultService;
import com.koreantutor.leveltest.LevelTestResultService.ResultView;
import com.koreantutor.lesson.LessonDtos.LessonView;
import com.koreantutor.lesson.LessonService;
import com.koreantutor.record.RecordDtos.RecordView;
import com.koreantutor.record.RecordService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** 대시보드 "할 일" (PRD F5-3) */
@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final LessonService lessons;
    private final RecordService records;
    private final LevelTestResultService levelTests;

    public DashboardController(LessonService lessons, RecordService records, LevelTestResultService levelTests) {
        this.lessons = lessons;
        this.records = records;
        this.levelTests = levelTests;
    }

    /**
     * pendingRecords: AI 초안은 나왔지만 아직 승인하지 않은 수업 후 기록
     * pendingPrep:    준비를 시작했지만 아직 확정하지 않은 수업안
     * toRecord:       수업안은 확정했는데 수업 후 기록을 아직 쓰지 않은 수업 (수업일이 오늘 이전)
     * pendingLevelTests: 저장했지만 아직 학생 카드에 반영하지 않은 레벨테스트 결과 (기획 ADR-0021)
     */
    public record Todos(List<RecordView> pendingRecords, List<LessonView> pendingPrep, List<LessonView> toRecord,
                        List<ResultView> pendingLevelTests) {
    }

    @GetMapping("/todos")
    public Todos todos() {
        return new Todos(records.pending(), lessons.pendingPrep(), lessons.toRecord(), levelTests.pending());
    }
}
