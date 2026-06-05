package com.mykb.repository;

import com.mykb.entity.KnowledgeBase;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface KnowledgeBaseRepository extends JpaRepository<KnowledgeBase, Long> {

    Page<KnowledgeBase> findByUserId(Long userId, Pageable pageable);

    long countByUserId(Long userId);
}
