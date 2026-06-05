package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.chat.ChatServiceGrpc;
import com.mykb.proto.chat.RagChatChunk;
import com.mykb.proto.chat.RagChatRequest;
import com.mykb.proto.chat.ChatMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class ChatClient {

    private final ChatServiceGrpc.ChatServiceStub stub;

    public Iterator<RagChatChunk> ragChat(String sessionId, String query, Long kbId, String kbName) {
        try {
            RagChatRequest request = RagChatRequest.newBuilder()
                    .setQuery(query)
                    .setKbId(kbId)
                    .setKbName(kbName != null ? kbName : "")
                    .setSessionId(sessionId != null ? sessionId : "")
                    .setTopK(5)
                    .build();
            Iterator<RagChatChunk> responses = stub.ragChat(request);
            log.info("gRPC ragChat initiated: sessionId={}, query={}, kbId={}", sessionId, query, kbId);
            if (responses == null) {
                throw new BusinessException("RAG chat returned null response from Python service");
            }
            return responses;
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("gRPC ragChat failed: sessionId={}, query={}, kbId={}, error={}", sessionId, query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to chat with Python RAG service: " + e.getMessage());
        }
    }
}
