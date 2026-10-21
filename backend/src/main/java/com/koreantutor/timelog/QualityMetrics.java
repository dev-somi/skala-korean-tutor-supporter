package com.koreantutor.timelog;

import com.koreantutor.lesson.ReviewDecision;

import java.util.*;
import java.util.function.Function;

/**
 * 주 지표: AI 초안을 선생님이 고치지 않고 그대로 승인한 비율 (기획 ADR-0020).
 * DB 없이 계산만 하는 함수라 단위 테스트로 규칙을 고정한다.
 */
public final class QualityMetrics {

    private QualityMetrics() {
    }

    public record Rate(int total, int kept, Double percent) {
        static Rate of(int total, int kept) {
            return new Rate(total, kept, total == 0 ? null : Math.round(1000.0 * kept / total) / 10.0);
        }
    }

    /** 수업안: 수업·범주마다 첫 결정만 본다. 첫 결정이 approve면 초안을 그대로 쓴 것이다. 범주별 + 전체 */
    public static Map<String, Rate> firstApproveRates(List<ReviewDecision> decisions) {
        Map<String, String> first = new LinkedHashMap<>(); // "lessonId/category" → 첫 action
        for (ReviewDecision d : decisions) {
            first.putIfAbsent(d.getLessonId() + "/" + d.getCategory(), d.getAction());
        }
        Map<String, int[]> counts = new LinkedHashMap<>();
        for (String c : List.of("review", "new_vocab", "new_grammar", "homework", "all")) counts.put(c, new int[2]);
        first.forEach((key, action) -> {
            String category = key.substring(key.indexOf('/') + 1);
            for (String c : List.of(category, "all")) {
                int[] n = counts.get(c);
                n[0]++;
                if ("approve".equals(action)) n[1]++;
            }
        });
        Map<String, Rate> result = new LinkedHashMap<>();
        counts.forEach((c, n) -> result.put(c, Rate.of(n[0], n[1])));
        return result;
    }

    /**
     * 수업 후 기록: AI 초안 항목 중 승인본에 그대로 남은 항목 수.
     * 초안은 ai-server 모양(snake_case), 승인본은 Spring 요청 모양(camelCase)이라 칸마다 비교 키를 맞춘다.
     * 고쳐서 승인한 항목은 글자가 달라져 "그대로"로 세지 않는다. 체크를 풀어 뺀 항목도 마찬가지다.
     */
    public static Map<String, Rate> keptDraftItems(List<Map<String, Object>[]> draftAndApproved) {
        Map<String, int[]> counts = new LinkedHashMap<>();
        for (String f : List.of("covered_item_ids", "strengths", "errors", "weakness_changes", "homework", "all")) counts.put(f, new int[2]);

        for (Map<String, Object>[] pair : draftAndApproved) {
            Map<String, Object> draft = pair[0], approved = pair[1];
            add(counts, "covered_item_ids", list(draft, "covered_item_ids"), list(approved, "coveredItemIds"), String::valueOf, String::valueOf);
            add(counts, "strengths", list(draft, "strengths"), list(approved, "strengths"), String::valueOf, String::valueOf);
            add(counts, "errors", list(draft, "errors"), list(approved, "errors"), Function.identity(), Function.identity());
            add(counts, "homework", list(draft, "homework"), list(approved, "homework"), Function.identity(), Function.identity());
            add(counts, "weakness_changes", list(draft, "weakness_changes"), list(approved, "weaknessChanges"),
                    o -> weaknessKey((Map<?, ?>) o, "item_id"), o -> weaknessKey((Map<?, ?>) o, "itemId"));
        }
        Map<String, Rate> result = new LinkedHashMap<>();
        counts.forEach((f, n) -> result.put(f, Rate.of(n[0], n[1])));
        return result;
    }

    private static List<Object> weaknessKey(Map<?, ?> m, String itemKey) {
        return Arrays.asList(m.get("action"), m.get(itemKey), m.get("description"));
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Map<String, Object> m, String key) {
        Object v = m == null ? null : m.get(key);
        return v instanceof List<?> l ? (List<Object>) l : List.of();
    }

    /** 초안 항목마다 승인본에서 같은 것을 하나씩 짝지어 지운다 (같은 항목이 두 번 있어도 두 번 세지 않게) */
    private static void add(Map<String, int[]> counts, String field, List<Object> draft, List<Object> approved,
                            Function<Object, Object> draftKey, Function<Object, Object> approvedKey) {
        List<Object> remaining = new ArrayList<>(approved.stream().map(approvedKey).toList());
        int kept = 0;
        for (Object item : draft) {
            if (remaining.remove(draftKey.apply(item))) kept++;
        }
        for (String f : List.of(field, "all")) {
            counts.get(f)[0] += draft.size();
            counts.get(f)[1] += kept;
        }
    }
}
