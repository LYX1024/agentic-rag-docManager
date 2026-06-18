package com.mykb.config;

import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.router.SaRouter;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class SaTokenConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> {
                    SaRouter
                        .match("/api/**")
                        .notMatch("/api/auth/login")
                        .notMatch("/api/auth/register")
                        .notMatch("/api/chat/session/*/history")
                        .notMatch("/api/chat/session/*/message")
                        .notMatch("/health")
                        .notMatch("/actuator/**")
                        .check(r -> StpUtil.checkLogin());
                }))
                .addPathPatterns("/**");
    }
}
