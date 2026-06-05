package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.common.Common;
import com.mykb.proto.kb.KBManagementServiceGrpc;
import com.mykb.proto.kb.KbManagement;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class KBManagementClient {

    private final KBManagementServiceGrpc.KBManagementServiceBlockingStub stub;

    public String createKB(String name, String description, String vsType, String embedModel, Long ownerId) {
        try {
            Common.OwnerRef owner = Common.OwnerRef.newBuilder()
                    .setOwnerId(ownerId.toString())
                    .build();
            KbManagement.CreateKBRequest request = KbManagement.CreateKBRequest.newBuilder()
                    .setName(name)
                    .setDescription(description != null ? description : "")
                    .setVsType(vsType != null ? vsType : "FAISS")
                    .setEmbedModel(embedModel != null ? embedModel : "bge-m3")
                    .setOwner(owner)
                    .build();
            KbManagement.CreateKBResponse response = stub.createKB(request);
            log.info("gRPC createKB success: kbId={}, vsId={}", response.getKbId(), response.getVsId());
            return response.getKbId();
        } catch (Exception e) {
            log.error("gRPC createKB failed: {}", e.getMessage(), e);
            throw new BusinessException("Failed to create knowledge base on Python service: " + e.getMessage());
        }
    }

    public void deleteKB(Long kbId) {
        try {
            KbManagement.DeleteKBRequest request = KbManagement.DeleteKBRequest.newBuilder()
                    .setKbId(kbId.toString())
                    .build();
            stub.deleteKB(request);
            log.info("gRPC deleteKB success: kbId={}", kbId);
        } catch (Exception e) {
            log.error("gRPC deleteKB failed: kbId={}, error={}", kbId, e.getMessage(), e);
            throw new BusinessException("Failed to delete knowledge base on Python service: " + e.getMessage());
        }
    }

    public KbManagement.KBStatsResponse getStats(Long kbId) {
        try {
            KbManagement.KBStatsRequest request = KbManagement.KBStatsRequest.newBuilder()
                    .setKbId(kbId.toString())
                    .build();
            KbManagement.KBStatsResponse response = stub.getStats(request);
            log.info("gRPC getStats success: kbId={}", kbId);
            return response;
        } catch (Exception e) {
            log.error("gRPC getStats failed: kbId={}, error={}", kbId, e.getMessage(), e);
            throw new BusinessException("Failed to get knowledge base stats: " + e.getMessage());
        }
    }
}
