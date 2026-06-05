package com.mykb.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.mykb.dto.ApiResponse;
import com.mykb.entity.KnowledgeFile;
import com.mykb.service.DocumentService;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
                                              @RequestParam @NotNull MultipartFile file,
                                              @RequestParam(required = false) String category) {
        log.info("Upload file: kbId={}, fileName={}, size={}, category={}", kbId, file.getOriginalFilename(), file.getSize(), category);
        KnowledgeFile result = documentService.uploadFile(kbId, file, category);
        return ApiResponse.success(result);
    }

    @GetMapping("/list")
    public ApiResponse<IPage<KnowledgeFile>> list(@RequestParam @NotNull Long kbId,
                                                  @RequestParam(required = false) String category,
                                                  @RequestParam(defaultValue = "0") int page,
                                                  @RequestParam(defaultValue = "10") int size) {
        IPage<KnowledgeFile> files = documentService.listDocuments(kbId, category, page + 1, size);
        return ApiResponse.success(files);
    }

    @GetMapping("/categories")
    public ApiResponse<java.util.List<String>> categories(@RequestParam @NotNull Long kbId) {
        return ApiResponse.success(documentService.getCategories(kbId));
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
