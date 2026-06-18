package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.kb.CreateKBRequest;
import com.mykb.proto.kb.DeleteKBRequest;
import com.mykb.proto.kb.GetKBStatsRequest;
import com.mykb.proto.kb.KBInfo;
import com.mykb.proto.kb.KBManagementServiceGrpc;
import com.mykb.proto.kb.KBStatsResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class KBManagementClient {

    private final KBManagementServiceGrpc.KBManagementServiceBlockingStub stub;

    public void createKB(String name, String description, String vsType, String embedModel, Long kbId) {
        try {
            CreateKBRequest request = CreateKBRequest.newBuilder()
                    .setName(name)
                    .setDescription(description != null ? description : "")
                    .setUserId(kbId)
                    .setVsTypeValue(vsType != null && vsType.equals("FAISS") ? 0 : 1)
                    .setEmbedModelValue(0)
                    .build();
            @SuppressWarnings("unused")
            KBInfo response = stub.createKB(request);
            log.info("gRPC createKB success: kbName={}", name);
        } catch (Exception e) {
            log.error("gRPC createKB failed: {}", e.getMessage(), e);
            throw new BusinessException("Failed to create knowledge base on Python service: " + e.getMessage());
        }
    }

    public void deleteKB(Long kbId) {
        try {
            DeleteKBRequest request = DeleteKBRequest.newBuilder()
                    .setKbId(kbId)
                    .build();
            stub.deleteKB(request);
            log.info("gRPC deleteKB success: kbId={}", kbId);
        } catch (Exception e) {
            log.error("gRPC deleteKB failed: kbId={}, error={}", kbId, e.getMessage(), e);
            throw new BusinessException("Failed to delete knowledge base on Python service: " + e.getMessage());
        }
    }

    public KBStatsResponse getStats(Long kbId) {
        try {
            GetKBStatsRequest request = GetKBStatsRequest.newBuilder()
                    .setKbId(kbId)
                    .build();
            KBStatsResponse response = stub.getKBStats(request);
            log.info("gRPC getStats success: kbId={}", kbId);
            return response;
        } catch (Exception e) {
            log.error("gRPC getStats failed: kbId={}, error={}", kbId, e.getMessage(), e);
            throw new BusinessException("Failed to get knowledge base stats: " + e.getMessage());
        }
    }
}
