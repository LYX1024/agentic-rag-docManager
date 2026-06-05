package com.mykb.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.mykb.dto.ApiResponse;
import com.mykb.dto.LoginRequest;
import com.mykb.dto.RegisterRequest;
import com.mykb.entity.User;
import com.mykb.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    @PostMapping("/login")
    public ApiResponse<String> login(@Valid @RequestBody LoginRequest request) {
        String token = userService.login(request);
        return ApiResponse.success(token);
    }

    @PostMapping("/register")
    public ApiResponse<User> register(@Valid @RequestBody RegisterRequest request) {
        User user = userService.register(request);
        return ApiResponse.success(user);
    }

    @GetMapping("/me")
    public ApiResponse<User> me(HttpServletRequest request) {
        long userId = StpUtil.getLoginIdAsLong();
        User user = userService.getUserById(userId);
        return ApiResponse.success(user);
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout() {
        StpUtil.logout();
        return ApiResponse.success();
    }
}
