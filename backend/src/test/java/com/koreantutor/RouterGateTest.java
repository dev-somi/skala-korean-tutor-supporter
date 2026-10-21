package com.koreantutor;

import com.koreantutor.chat.RouteDecision;
import com.koreantutor.chat.RouterService;
import com.koreantutor.student.Student;
import com.koreantutor.student.StudentRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;

/** 라우터 권위 게이트: LLM이 고른 intent·학생 이름을 코드가 DB 기준으로 고친다 */
@Import(TestcontainersConfiguration.class)
@SpringBootTest
class RouterGateTest {

    @Autowired RouterService router;
    @Autowired StudentRepository students;

    @Test
    void unknownStudentForWorkRequestBecomesGeneral() {
        var resolved = router.resolve(new RouteDecision("lesson_prep", "없는학생", 40, "r"));
        assertThat(resolved.studentNotFound()).isTrue();
        assertThat(resolved.decision().intent()).isEqualTo("general");
    }

    @Test
    void partialNameMatchesSingleStudent() {
        students.save(new Student("다나카 하루토", "ja"));
        var resolved = router.resolve(new RouteDecision("post_lesson", "하루토", null, "r"));
        assertThat(resolved.student()).isNotNull();
        assertThat(resolved.decision().intent()).isEqualTo("post_lesson");
    }

    @Test
    void unknownIntentBecomesGeneral() {
        assertThat(router.resolve(new RouteDecision("delete_everything", null, null, "r")).decision().intent())
                .isEqualTo("general");
    }

    @Test
    void grammarQuestionWithoutStudentIsAllowed() {
        var resolved = router.resolve(new RouteDecision("grammar_qa", null, null, "r"));
        assertThat(resolved.studentNotFound()).isFalse();
        assertThat(resolved.decision().intent()).isEqualTo("grammar_qa");
    }

    @Test
    void grammarQuestionKeepsNamedStudentForLevel() {
        students.save(new Student("스즈키 유이", "ja"));
        var resolved = router.resolve(new RouteDecision("grammar_qa", "유이", null, "r"));
        assertThat(resolved.student()).isNotNull();
        assertThat(resolved.decision().intent()).isEqualTo("grammar_qa");
    }

    @Test
    void lookupWithoutStudentIsAllowed() {
        var resolved = router.resolve(new RouteDecision("lookup", null, null, "r"));
        assertThat(resolved.studentNotFound()).isFalse();
        assertThat(resolved.decision().intent()).isEqualTo("lookup");
    }
}
