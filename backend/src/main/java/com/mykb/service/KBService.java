package com.mykb.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.mykb.dto.KBCreateRequest;
import com.mykb.entity.KnowledgeBase;
import com.mykb.exception.BusinessException;
import com.mykb.grpc.client.KBManagementClient;
import com.mykb.mapper.KnowledgeBaseMapper;
import com.mykb.mapper.KnowledgeFileMapper;
import com.mykb.proto.kb.KBStatsResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class KBService {

    private final KnowledgeBaseMapper kbMapper;
    private final KnowledgeFileMapper fileMapper;
    private final KBManagementClient kbManagementClient;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public KBService(KnowledgeBaseMapper kbMapper, KnowledgeFileMapper fileMapper,
                     KBManagementClient kbManagementClient, StringRedisTemplate redis,
                     ObjectMapper objectMapper) {
        this.kbMapper = kbMapper;
        this.fileMapper = fileMapper;
        this.kbManagementClient = kbManagementClient;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

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

        // Evict cache
        try {
            redis.delete("kb:list:" + userId);
        } catch (Exception e) {
            log.warn("Cache eviction failed for createKB: {}", e.getMessage());
        }

        return kb;
    }

    public Page<KnowledgeBase> listKBs(Long userId, int pageNum, int pageSize) {
        String cacheKey = "kb:list:" + userId;

        // Try cache first
        try {
            String cached = redis.opsForValue().get(cacheKey);
            if (cached != null) {
                JsonNode node = objectMapper.readTree(cached);
                List<KnowledgeBase> records = objectMapper.readValue(
                        node.get("records").traverse(),
                        objectMapper.getTypeFactory().constructCollectionType(List.class, KnowledgeBase.class));
                long total = node.get("total").asLong();
                Page<KnowledgeBase> page = new Page<>(pageNum, pageSize, total);
                page.setRecords(records);
                log.debug("Cache hit: {}", cacheKey);
                return page;
            }
        } catch (Exception e) {
            log.warn("Cache read failed for listKBs: {}", e.getMessage());
        }

        // Query MySQL + populate fileCount
        Page<KnowledgeBase> page = new Page<>(pageNum, pageSize);
        Page<KnowledgeBase> result = kbMapper.selectPage(page, new LambdaQueryWrapper<KnowledgeBase>()
                .eq(KnowledgeBase::getUserId, userId)
                .orderByDesc(KnowledgeBase::getCreatedAt));
        for (KnowledgeBase kb : result.getRecords()) {
            kb.setFileCount(fileMapper.countByKbId(kb.getId()).intValue());
        }

        // Cache the result
        try {
            Map<String, Object> cacheValue = new HashMap<>();
            cacheValue.put("records", result.getRecords());
            cacheValue.put("total", result.getTotal());
            redis.opsForValue().set(cacheKey, objectMapper.writeValueAsString(cacheValue), Duration.ofMinutes(5));
        } catch (Exception e) {
            log.warn("Cache write failed for listKBs: {}", e.getMessage());
        }

        return result;
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

        // Evict cache
        try {
            redis.delete("kb:list:" + kb.getUserId());
            redis.delete("kb:stats:" + kbId);
        } catch (Exception e) {
            log.warn("Cache eviction failed for deleteKB: {}", e.getMessage());
        }

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

        // Evict cache
        try {
            redis.delete("kb:list:" + kb.getUserId());
        } catch (Exception e) {
            log.warn("Cache eviction failed for updateKB: {}", e.getMessage());
        }

        log.info("KB updated: kbId={}", kbId);
        return kb;
    }

    public Map<String, Object> getKBStats(Long kbId) {
        String cacheKey = "kb:stats:" + kbId;

        // Try cache first
        try {
            String cached = redis.opsForValue().get(cacheKey);
            if (cached != null) {
                log.debug("Cache hit: {}", cacheKey);
                return objectMapper.readValue(cached, new TypeReference<Map<String, Object>>() {});
            }
        } catch (Exception e) {
            log.warn("Cache read failed for getKBStats: {}", e.getMessage());
        }

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

        // Cache the result
        try {
            redis.opsForValue().set(cacheKey, objectMapper.writeValueAsString(stats), Duration.ofMinutes(5));
        } catch (Exception e) {
            log.warn("Cache write failed for getKBStats: {}", e.getMessage());
        }

        return stats;
    }

    /**
     * Evict file count cache for a KB. Called by DocumentService when files change.
     */
    public void evictFileCountCache(Long kbId) {
        try {
            redis.delete("kb:stats:" + kbId);
            KnowledgeBase kb = kbMapper.selectById(kbId);
            if (kb != null) {
                redis.delete("kb:list:" + kb.getUserId());
            }
        } catch (Exception e) {
            log.warn("Cache eviction failed for evictFileCountCache: kbId={}, error={}", kbId, e.getMessage());
        }
    }
}
