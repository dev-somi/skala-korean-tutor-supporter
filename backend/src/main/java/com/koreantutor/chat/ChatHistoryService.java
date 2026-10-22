package com.koreantutor.chat;

import com.koreantutor.common.NotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

/** 채팅 대화 기록 저장·조회 (기술 ADR-0041) */
@Service
public class ChatHistoryService {

    private final ChatConversationRepository conversations;
    private final ChatMessageRepository messages;

    public ChatHistoryService(ChatConversationRepository conversations, ChatMessageRepository messages) {
        this.conversations = conversations;
        this.messages = messages;
    }

    /** 질문과 답을 한 번에 남긴다. 첫 질문이면 대화를 만든다 */
    @Transactional
    public void saveTurn(String conversationId, String question, String answer, Map<String, Object> meta) {
        ChatConversation conversation = conversations.findById(conversationId)
                .orElseGet(() -> conversations.save(new ChatConversation(conversationId, question)));
        conversation.touch();
        messages.save(new ChatMessage(conversationId, ChatMessage.USER, question, Map.of()));
        messages.save(new ChatMessage(conversationId, ChatMessage.ASSISTANT, answer, meta));
    }

    @Transactional(readOnly = true)
    public List<ChatConversation> list() {
        return conversations.findAllByOrderByUpdatedAtDesc();
    }

    @Transactional(readOnly = true)
    public List<ChatMessage> messages(String conversationId) {
        find(conversationId);
        return messages.findByConversationIdOrderByIdAsc(conversationId);
    }

    @Transactional
    public ChatConversation rename(String conversationId, String title) {
        ChatConversation conversation = find(conversationId);
        conversation.rename(title.strip());
        return conversation;
    }

    @Transactional
    public void delete(String conversationId) {
        conversations.delete(find(conversationId));
    }

    private ChatConversation find(String conversationId) {
        return conversations.findById(conversationId).orElseThrow(() -> new NotFoundException("chat_conversation", conversationId));
    }
}
