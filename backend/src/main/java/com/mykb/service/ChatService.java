package com.mykb.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mykb.dto.ChatSessionCreateRequest;
import com.mykb.entity.ChatMessage;
import com.mykb.entity.ChatSession;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.ChatClient;
import com.mykb.mapper.ChatMessageMapper;
import com.mykb.mapper.ChatSessionMapper;
import com.mykb.proto.chat.RagChatChunk;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

@Slf4j
@Service
public class ChatService {

    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final ChatClient chatClient;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public ChatService(ChatSessionMapper sessionMapper, ChatMessageMapper messageMapper,
                       ChatClient chatClient, StringRedisTemplate redisTemplate,
                       ObjectMapper objectMapper) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.chatClient = chatClient;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public ChatSession createSession(Long userId, ChatSessionCreateRequest request) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setKbId(request.kbId());
        session.setTitle(request.title() != null ? request.title() : "New Chat");
        sessionMapper.insert(session);
        evictSessionCache(userId);
        log.info("Chat session created: sessionId={}, userId={}, kbId={}", session.getId(), userId, request.kbId());
        return session;
    }

    public List<ChatSession> listSessions(Long userId) {
        String cacheKey = "chat:sessions:" + userId;
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                return objectMapper.readValue(cached, new TypeReference<List<ChatSession>>() {});
            }
        } catch (Exception e) {
            log.warn("Redis sessions cache read failed: {}", e.getMessage());
        }

        List<ChatSession> sessions = sessionMapper.selectByUserId(userId);
        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(sessions), Duration.ofMinutes(10));
        } catch (Exception e) {
            log.warn("Redis sessions cache write failed: {}", e.getMessage());
        }
        return sessions;
    }

    public ChatMessage saveMessage(Long sessionId, String role, String content, String sources) {
        ChatMessage message = new ChatMessage();
        message.setSessionId(sessionId);
        message.setRole(role);
        message.setContent(content);
        message.setSources(sources);
        messageMapper.insert(message);
        evictHistoryCache(sessionId);
        log.info("Chat message saved: msgId={}, sessionId={}, role={}", message.getId(), sessionId, role);
        return message;
    }

    public List<ChatMessage> getHistory(Long sessionId) {
        String cacheKey = "chat:history:" + sessionId;
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                return objectMapper.readValue(cached, new TypeReference<List<ChatMessage>>() {});
            }
        } catch (Exception e) {
            log.warn("Redis history cache read failed: {}", e.getMessage());
        }

        List<ChatMessage> messages = messageMapper.selectBySessionIdOrderByCreatedAtAsc(sessionId);
        try {
            redisTemplate.opsForValue().set(cacheKey, objectMapper.writeValueAsString(messages), Duration.ofMinutes(30));
        } catch (Exception e) {
            log.warn("Redis history cache write failed: {}", e.getMessage());
        }
        return messages;
    }

    public Iterator<RagChatChunk> ragChat(String sessionId, String query, Long kbId) {
        log.info("Starting RAG chat: sessionId={}, query={}, kbId={}", sessionId, query, kbId);
        return chatClient.ragChat(sessionId, query, kbId, "");
    }

    public ChatSession getSession(Long sessionId) {
        ChatSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new BusinessException(404, "Chat session not found");
        }
        return session;
    }

    public void evictSessionCache(Long userId) {
        redisTemplate.delete("chat:sessions:" + userId);
    }

    public void evictHistoryCache(Long sessionId) {
        redisTemplate.delete("chat:history:" + sessionId);
    }
}
