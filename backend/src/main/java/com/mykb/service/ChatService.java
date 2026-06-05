package com.mykb.service;

import com.mykb.dto.ChatSessionCreateRequest;
import com.mykb.entity.ChatMessage;
import com.mykb.entity.ChatSession;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.ChatClient;
import com.mykb.proto.chat.RagChatChunk;
import com.mykb.repository.ChatMessageRepository;
import com.mykb.repository.ChatSessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Iterator;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ChatSessionRepository sessionRepository;
    private final ChatMessageRepository messageRepository;
    private final ChatClient chatClient;

    public ChatSession createSession(Long userId, ChatSessionCreateRequest request) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setKbId(request.kbId());
        session.setTitle(request.title() != null ? request.title() : "New Chat");
        ChatSession saved = sessionRepository.save(session);
        log.info("Chat session created: sessionId={}, userId={}, kbId={}", saved.getId(), userId, request.kbId());
        return saved;
    }

    public List<ChatSession> listSessions(Long userId) {
        return sessionRepository.findByUserId(userId);
    }

    @Transactional
    public ChatMessage saveMessage(Long sessionId, String role, String content, String sources) {
        ChatMessage message = new ChatMessage();
        message.setSessionId(sessionId);
        message.setRole(role);
        message.setContent(content);
        message.setSources(sources);
        ChatMessage saved = messageRepository.save(message);
        log.info("Chat message saved: msgId={}, sessionId={}, role={}", saved.getId(), sessionId, role);
        return saved;
    }

    public List<ChatMessage> getHistory(Long sessionId) {
        return messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
    }

    public Iterator<RagChatChunk> ragChat(String sessionId, String query, Long kbId) {
        log.info("Starting RAG chat: sessionId={}, query={}, kbId={}", sessionId, query, kbId);
        return chatClient.ragChat(sessionId, query, kbId, "");
    }

    public ChatSession getSession(Long sessionId) {
        return sessionRepository.findById(sessionId)
                .orElseThrow(() -> new BusinessException(404, "Chat session not found"));
    }
}
