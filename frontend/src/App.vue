<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">指标服务与数据开放平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向指标口径管理、数据服务编排、API发布与调用治理的数据开放与分析平台。</span>
        <span class="head-user">当前值班：{{ store.operator }} · {{ store.shiftLabel }}</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()

const navItems = [{ label: "运营概览", path: "/" }, { label: "指标域管理", path: "/metric_domain" }, { label: "派生指标", path: "/derived_metric" }, { label: "API服务", path: "/api_service" }, { label: "查询优化", path: "/query_optimize" }, { label: "优化分析报告", path: "/optimize_report" }, { label: "执行计划视图", path: "/plan_decision" }, { label: "接口订阅", path: "/api_subscribe" }, { label: "调用凭证", path: "/call_credential" }, { label: "数据源连接", path: "/datasource_connect" }, { label: "调用追踪", path: "/call_trace" }, { label: "数据预览", path: "/data_preview" }, { label: "接口版本", path: "/api_version" }, { label: "批量导出", path: "/batch_export" }, { label: "指标重名解析", path: "/metric_homonym" }, { label: "数据聚合", path: "/data_aggregate" }, { label: "数据清洗", path: "/data_cleanse" }, { label: "访问看板", path: "/access_dashboard" }, { label: "SQL模板", path: "/sql_template" }, { label: "结果缓存", path: "/result_cache" }, { label: "查询审计", path: "/query_audit" }]
</script>
