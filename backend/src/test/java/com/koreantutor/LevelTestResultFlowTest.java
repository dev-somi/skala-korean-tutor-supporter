package com.koreantutor;

import com.koreantutor.aiclient.AiServerClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * 레벨테스트 결과 저장 → 할 일에 뜸 → 선생님이 확인하면 학생 카드에 반영 (기획 ADR-0021).
 * ai-server는 가짜(AiServerClient mock), DB는 Testcontainers Postgres.
 */
@Import(TestcontainersConfiguration.class)
@SpringBootTest
@AutoConfigureMockMvc
class LevelTestResultFlowTest {

    @Autowired MockMvc mvc;
    @Autowired JsonMapper json;

    @MockitoBean AiServerClient aiServer;

    long saveResult(String note) throws Exception {
        String res = mvc.perform(post("/api/level-test/results").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answers\":{\"hangul-1\":true,\"L1-g1\":true,\"L2-g1\":false},\"note\":\"" + note + "\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.suggestedLevel").value(2))
                .andExpect(jsonPath("$.status").value("pending"))
                .andExpect(jsonPath("$.answered").value(3))
                .andReturn().getResponse().getContentAsString();
        return json.readTree(res).get("id").asLong();
    }

    long createStudent(String level) throws Exception {
        String body = "{\"name\":\"레벨 테스트\",\"nativeLanguage\":\"en\",\"standardLevel\":1,\"level\":\"" + level + "\"}";
        String res = mvc.perform(post("/api/students").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(res).get("id").asLong();
    }

    @Test
    void savedResultWaitsForTeacherThenUpdatesStudentCard() throws Exception {
        when(aiServer.levelTestScore(anyMap())).thenReturn(Map.of("suggested_level", 2, "reason", "2급 1/4개"));
        long resultId = saveResult("받침 발음 약함");
        long studentId = createStudent("");

        // 저장만으로는 학생 카드가 바뀌지 않는다
        mvc.perform(get("/api/students/{id}", studentId)).andExpect(jsonPath("$.standardLevel").value(1));
        mvc.perform(get("/api/dashboard/todos"))
                .andExpect(jsonPath("$.pendingLevelTests[?(@.id == " + resultId + ")]").exists());

        mvc.perform(post("/api/level-test/results/{id}/apply", resultId).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"studentId\":" + studentId + "}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("applied"))
                .andExpect(jsonPath("$.appliedLevel").value(2));

        mvc.perform(get("/api/students/{id}", studentId))
                .andExpect(jsonPath("$.standardLevel").value(2))
                .andExpect(jsonPath("$.levelAssessedOn").isNotEmpty())
                .andExpect(jsonPath("$.level").value("받침 발음 약함"));
        mvc.perform(get("/api/dashboard/todos"))
                .andExpect(jsonPath("$.pendingLevelTests[?(@.id == " + resultId + ")]").doesNotExist());

        // 한 번 확인한 결과는 다시 반영할 수 없다
        mvc.perform(post("/api/level-test/results/{id}/apply", resultId).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"studentId\":" + studentId + "}"))
                .andExpect(status().isConflict());
    }

    @Test
    void teacherCanOverrideLevelAndKeepsExistingMemo() throws Exception {
        when(aiServer.levelTestScore(anyMap())).thenReturn(Map.of("suggested_level", 2, "reason", "2급 1/4개"));
        long resultId = saveResult("새 메모");
        long studentId = createStudent("기존 메모");

        mvc.perform(post("/api/level-test/results/{id}/apply", resultId).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"studentId\":" + studentId + ",\"level\":3}"))
                .andExpect(jsonPath("$.appliedLevel").value(3));
        mvc.perform(get("/api/students/{id}", studentId))
                .andExpect(jsonPath("$.standardLevel").value(3))
                .andExpect(jsonPath("$.level").value("기존 메모"));
    }

    @Test
    void dismissedResultLeavesTodos() throws Exception {
        when(aiServer.levelTestScore(anyMap())).thenReturn(Map.of("suggested_level", 2, "reason", "2급 1/4개"));
        long resultId = saveResult("");
        mvc.perform(post("/api/level-test/results/{id}/dismiss", resultId))
                .andExpect(jsonPath("$.status").value("dismissed"));
        mvc.perform(get("/api/level-test/results"))
                .andExpect(jsonPath("$[?(@.id == " + resultId + ")]").doesNotExist());
    }

    @Test
    void emptyAnswersAreRejected() throws Exception {
        mvc.perform(post("/api/level-test/results").contentType(MediaType.APPLICATION_JSON).content("{\"answers\":{}}"))
                .andExpect(status().isBadRequest());
    }
}
