package com.mykb.repository;

import com.mykb.entity.FileChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileChunkRepository extends JpaRepository<FileChunk, Long> {

    List<FileChunk> findByFileId(Long fileId);

    Optional<FileChunk> findByVsDocId(String vsDocId);

    void deleteByFileId(Long fileId);
}
