package com.mykb.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mykb.dto.KBCreateRequest;
import com.mykb.entity.KnowledgeBase;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.KBManagementClient;
import com.mykb.mapper.KnowledgeBaseMapper;
import com.mykb.mapper.KnowledgeFileMapper;
import com.mykb.proto.kb.KBStatsResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class KBService {

    private final KnowledgeBaseMapper kbMapper;
    private final KnowledgeFileMapper fileMapper;
    private final KBManagementClient kbManagementClient;

    public KnowledgeBase createKB(KBCreateRequest request, Long userId) {
        KnowledgeBase kb = new KnowledgeBase();
        kb.setName(request.name());
        kb.setDescription(request.description());
        kb.setVsType(request.vsType() != null ? request.vsType() : "FAISS");
        kb.setEmbedModel(request.embedModel() != null ? request.embedModel() : "bge-m3");
        kb.setUserId(userId);

        // Insert to MySQL first to get the ID
        kbMapper.insert(kb);

        // Init on Python side
        try {
            kbManagementClient.createKB(
                    kb.getName(),
                    kb.getDescription(),
                    kb.getVsType(),
                    kb.getEmbedModel(),
                    kb.getId());
            log.info("KB created: kbId={}, name={}", kb.getId(), kb.getName());
        } catch (Exception e) {
            log.error("Python init failed, rolling back: kbId={}, error={}", kb.getId(), e.getMessage());
            kbMapper.deleteById(kb.getId());
            throw new BusinessException("Failed to create knowledge base: " + e.getMessage());
        }

        return kb;
    }

    public Page<KnowledgeBase> listKBs(Long userId, int pageNum, int pageSize) {
        Page<KnowledgeBase> page = new Page<>(pageNum, pageSize);
        return kbMapper.selectPage(page, new LambdaQueryWrapper<KnowledgeBase>()
                .eq(KnowledgeBase::getUserId, userId)
                .orderByDesc(KnowledgeBase::getCreatedAt));
    }

    public void deleteKB(Long kbId) {
        KnowledgeBase kb = kbMapper.selectById(kbId);
        if (kb == null) {
            throw new BusinessException(404, "Knowledge base not found");
        }

        try {
            kbManagementClient.deleteKB(kbId);
        } catch (Exception e) {
            log.warn("Python KB cleanup failed (non-fatal): kbId={}, error={}", kbId, e.getMessage());
        }

        kbMapper.deleteById(kb.getId());
        log.info("KB deleted: kbId={}", kbId);
    }

    public KnowledgeBase getKB(Long kbId) {
        KnowledgeBase kb = kbMapper.selectById(kbId);
        if (kb == null) {
            throw new BusinessException(404, "Knowledge base not found");
        }
        return kb;
    }

    public KnowledgeBase updateKB(Long kbId, KBCreateRequest request) {
        KnowledgeBase kb = kbMapper.selectById(kbId);
        if (kb == null) {
            throw new BusinessException(404, "Knowledge base not found");
        }

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

        kbMapper.updateById(kb);
        log.info("KB updated: kbId={}", kbId);
        return kb;
    }

    public Map<String, Object> getKBStats(Long kbId) {
        KnowledgeBase kb = kbMapper.selectById(kbId);
        if (kb == null) {
            throw new BusinessException(404, "Knowledge base not found");
        }

        Map<String, Object> stats = new HashMap<>();
        stats.put("kbId", kb.getId());
        stats.put("name", kb.getName());
        stats.put("fileCount", fileMapper.countByKbId(kbId));

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
