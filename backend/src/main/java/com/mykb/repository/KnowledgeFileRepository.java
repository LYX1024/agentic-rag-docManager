package com.mykb.repository;

import com.mykb.entity.KnowledgeFile;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface KnowledgeFileRepository extends JpaRepository<KnowledgeFile, Long> {

    Page<KnowledgeFile> findByKbId(Long kbId, Pageable pageable);

    Page<KnowledgeFile> findByKbIdAndCategory(Long kbId, String category, Pageable pageable);

    List<KnowledgeFile> findByKbIdAndStatus(Long kbId, String status);

    long countByKbId(Long kbId);

    @Query("SELECT DISTINCT kf.category FROM KnowledgeFile kf WHERE kf.kbId = :kbId AND kf.category != ''")
    List<String> findDistinctCategoriesByKbId(@Param("kbId") Long kbId);
}
