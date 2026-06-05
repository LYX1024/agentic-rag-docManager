package com.mykb.controller;

import com.mykb.dto.ApiResponse;
import com.mykb.dto.SearchRequest;
import com.mykb.service.SearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SearchService searchService;

    @PostMapping
    public ApiResponse<Map<String, Object>> search(@Valid @RequestBody SearchRequest request) {
        Map<String, Object> result = searchService.search(request);
        return ApiResponse.success(result);
    }

    @PostMapping("/hybrid")
    public ApiResponse<Map<String, Object>> hybridSearch(@Valid @RequestBody SearchRequest request) {
        Map<String, Object> result = searchService.hybridSearch(request);
        return ApiResponse.success(result);
    }
}
