package com.mykb.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.mykb.dto.ApiResponse;
import com.mykb.entity.KnowledgeFile;
import com.mykb.service.DocumentService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

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

    @GetMapping("/{id}/content")
    public void preview(@PathVariable Long id, HttpServletResponse response) {
        KnowledgeFile kf = documentService.getFile(id);
        response.setContentType(getContentType(kf.getFileExt()));
        String encodedName = URLEncoder.encode(kf.getFileName(), StandardCharsets.UTF_8)
                .replace("+", "%20");
        response.setHeader("Content-Disposition",
                "inline; filename*=UTF-8''" + encodedName);
        try (InputStream in = documentService.getFileContent(id);
             OutputStream out = response.getOutputStream()) {
            in.transferTo(out);
        } catch (Exception e) {
            log.error("Preview failed: fileId={}, error={}", id, e.getMessage());
            throw new com.mykb.exception.BusinessException("Failed to preview file: " + e.getMessage());
        }
    }

    private String getContentType(String ext) {
        return switch (ext.toLowerCase()) {
            case ".pdf" -> "application/pdf";
            case ".docx", ".doc" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case ".md" -> "text/markdown; charset=UTF-8";
            case ".txt" -> "text/plain; charset=UTF-8";
            case ".png" -> "image/png";
            case ".jpg", ".jpeg" -> "image/jpeg";
            default -> "application/octet-stream";
        };
    }
}
