package com.koreantutor.chat;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    List<ChatMessage> findByConversationIdOrderByIdAsc(String conversationId);

    /** 최근 메시지부터. LLM 문맥용 */
    List<ChatMessage> findByConversationIdOrderByIdDesc(String conversationId, Pageable page);
}
