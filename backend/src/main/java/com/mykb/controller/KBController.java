package com.mykb.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mykb.dto.ApiResponse;
import com.mykb.dto.KBCreateRequest;
import com.mykb.entity.KnowledgeBase;
import com.mykb.service.KBService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/kb")
@RequiredArgsConstructor
public class KBController {

    private final KBService kbService;

    @PostMapping
    public ApiResponse<KnowledgeBase> create(@Valid @RequestBody KBCreateRequest request,
                                              HttpServletRequest httpRequest) {
        long userId = StpUtil.getLoginIdAsLong();
        KnowledgeBase kb = kbService.createKB(request, userId);
        return ApiResponse.success(kb);
    }

    @GetMapping
    public ApiResponse<Page<KnowledgeBase>> list(@RequestParam(defaultValue = "0") int page,
                                                  @RequestParam(defaultValue = "10") int size,
                                                  HttpServletRequest httpRequest) {
        long userId = StpUtil.getLoginIdAsLong();
        Page<KnowledgeBase> kbs = kbService.listKBs(userId, page, size);
        return ApiResponse.success(kbs);
    }

    @GetMapping("/{id}")
    public ApiResponse<KnowledgeBase> detail(@PathVariable Long id) {
        KnowledgeBase kb = kbService.getKB(id);
        return ApiResponse.success(kb);
    }

    @PutMapping("/{id}")
    public ApiResponse<KnowledgeBase> update(@PathVariable Long id,
                                              @Valid @RequestBody KBCreateRequest request) {
        KnowledgeBase kb = kbService.updateKB(id, request);
        return ApiResponse.success(kb);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        kbService.deleteKB(id);
        return ApiResponse.success();
    }

    @GetMapping("/{id}/stats")
    public ApiResponse<Map<String, Object>> stats(@PathVariable Long id) {
        Map<String, Object> stats = kbService.getKBStats(id);
        return ApiResponse.success(stats);
    }
}
