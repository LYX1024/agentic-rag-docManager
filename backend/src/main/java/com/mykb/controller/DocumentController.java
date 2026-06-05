package com.mykb.controller;

import com.mykb.dto.ApiResponse;
import com.mykb.entity.KnowledgeFile;
import com.mykb.service.DocumentService;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Slf4j
@RestController
@RequestMapping("/api/doc")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping("/upload")
    public ApiResponse<KnowledgeFile> upload(@RequestParam @NotNull Long kbId,
                                              @RequestParam @NotNull MultipartFile file) {
        log.info("Upload file: kbId={}, fileName={}, size={}", kbId, file.getOriginalFilename(), file.getSize());
        KnowledgeFile result = documentService.uploadFile(kbId, file);
        return ApiResponse.success(result);
    }

    @GetMapping("/list")
    public ApiResponse<Page<KnowledgeFile>> list(@RequestParam @NotNull Long kbId,
                                                  @RequestParam(defaultValue = "0") int page,
                                                  @RequestParam(defaultValue = "10") int size) {
        Page<KnowledgeFile> files = documentService.listDocuments(kbId, PageRequest.of(page, size));
        return ApiResponse.success(files);
    }

    @GetMapping("/{id}/status")
    public ApiResponse<String> status(@PathVariable Long id) {
        String status = documentService.getDocumentStatus(id);
        return ApiResponse.success(status);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return ApiResponse.success();
    }
}
