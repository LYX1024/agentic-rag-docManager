package com.mykb.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mykb.service.DocumentService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class RedisSubscriber implements MessageListener {

    private final RedisTemplate<String, String> redisTemplate;
    private final RedisMessageListenerContainer listenerContainer;
    private final DocumentService documentService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostConstruct
    public void init() {
        listenerContainer.addMessageListener(this, new ChannelTopic("ingestion:status"));
        log.info("Redis subscriber registered: channel=ingestion:status");
    }

    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            String body = new String(message.getBody());
            @SuppressWarnings("unchecked")
            Map<String, Object> data = objectMapper.readValue(body, Map.class);
            String minioKey = (String) data.get("minio_key");
            String status = (String) data.get("status");
            int chunkCount = data.get("chunk_count") != null ? ((Number) data.get("chunk_count")).intValue() : 0;
            String errorMsg = (String) data.getOrDefault("error_msg", "");
            documentService.syncIngestionStatus(minioKey, status, chunkCount, errorMsg);
        } catch (Exception e) {
            log.error("Failed to handle Redis message: {}", e.getMessage());
        }
    }
}
