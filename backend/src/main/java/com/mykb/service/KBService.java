package com.mykb.service;

import com.mykb.dto.KBCreateRequest;
import com.mykb.entity.KnowledgeBase;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.KBManagementClient;
import com.mykb.proto.kb.KBStatsResponse;
import com.mykb.repository.KnowledgeBaseRepository;
import com.mykb.repository.KnowledgeFileRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class KBService {

    private final KnowledgeBaseRepository kbRepository;
    private final KnowledgeFileRepository fileRepository;
    private final KBManagementClient kbManagementClient;

    public KnowledgeBase createKB(KBCreateRequest request, Long userId) {
        KnowledgeBase kb = new KnowledgeBase();
        kb.setName(request.name());
        kb.setDescription(request.description());
        kb.setVsType(request.vsType() != null ? request.vsType() : "FAISS");
        kb.setEmbedModel(request.embedModel() != null ? request.embedModel() : "bge-m3");
        kb.setUserId(userId);

        KnowledgeBase saved = kbRepository.save(kb);

        try {
            kbManagementClient.createKB(
                    saved.getName(),
                    saved.getDescription(),
                    saved.getVsType(),
                    saved.getEmbedModel(),
                    saved.getId());
            log.info("KB created on Python side: kbId={}", saved.getId());
        } catch (Exception e) {
            log.error("KB saved locally but Python init failed: kbId={}, error={}", saved.getId(), e.getMessage());
            throw new BusinessException("Knowledge base created locally but Python service init failed: " + e.getMessage());
        }

        return saved;
    }

    public Page<KnowledgeBase> listKBs(Long userId, PageRequest pageRequest) {
        return kbRepository.findByUserId(userId, pageRequest);
    }

    @Transactional
    public void deleteKB(Long kbId) {
        KnowledgeBase kb = kbRepository.findById(kbId)
                .orElseThrow(() -> new BusinessException(404, "Knowledge base not found"));

        try {
            kbManagementClient.deleteKB(kbId);
        } catch (Exception e) {
            log.warn("Python KB cleanup failed (non-fatal): kbId={}, error={}", kbId, e.getMessage());
        }

        kbRepository.delete(kb);
        log.info("KB deleted: kbId={}", kbId);
    }

    public KnowledgeBase updateKB(Long kbId, KBCreateRequest request) {
        KnowledgeBase kb = kbRepository.findById(kbId)
                .orElseThrow(() -> new BusinessException(404, "Knowledge base not found"));

        if (request.name() != null) {
            kb.setName(request.name());
        }
        if (request.description() != null) {
            kb.setDescription(request.description());
        }
        if (request.vsType() != null) {
            kb.setVsType(request.vsType());
        }
        if (request.embedModel() != null) {
            kb.setEmbedModel(request.embedModel());
        }

        KnowledgeBase updated = kbRepository.save(kb);
        log.info("KB updated: kbId={}", kbId);
        return updated;
    }

    public Map<String, Object> getKBStats(Long kbId) {
        KnowledgeBase kb = kbRepository.findById(kbId)
                .orElseThrow(() -> new BusinessException(404, "Knowledge base not found"));

        Map<String, Object> stats = new HashMap<>();
        stats.put("kbId", kb.getId());
        stats.put("name", kb.getName());
        stats.put("fileCount", fileRepository.countByKbId(kbId));

        try {
            KBStatsResponse grpcStats = kbManagementClient.getStats(kbId);
            stats.put("totalChunks", grpcStats.getChunkCount());
            stats.put("totalFileSize", grpcStats.getTotalFileSize());
        } catch (Exception e) {
            log.warn("Failed to get Python-side stats: kbId={}, error={}", kbId, e.getMessage());
            stats.put("totalChunks", 0);
            stats.put("totalFileSize", 0);
        }

        return stats;
    }
}
