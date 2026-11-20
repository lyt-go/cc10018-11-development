import { createRouter, createWebHistory } from 'vue-router'

import Overview from '@/views/Overview.vue'
const MetricDomain = () => import('@/views/metric_domain/index.vue')
const DerivedMetric = () => import('@/views/derived_metric/index.vue')
const ApiService = () => import('@/views/api_service/index.vue')
const QueryOptimize = () => import('@/views/query_optimize/index.vue')
const OptimizeReport = () => import('@/views/optimize_report/index.vue')
const PlanDecision = () => import('@/views/plan_decision/index.vue')
const ApiSubscribe = () => import('@/views/api_subscribe/index.vue')
const CallCredential = () => import('@/views/call_credential/index.vue')
const DatasourceConnect = () => import('@/views/datasource_connect/index.vue')
const CallTrace = () => import('@/views/call_trace/index.vue')
const DataPreview = () => import('@/views/data_preview/index.vue')
const ApiVersion = () => import('@/views/api_version/index.vue')
const BatchExport = () => import('@/views/batch_export/index.vue')
const MetricHomonym = () => import('@/views/metric_homonym/index.vue')
const DataAggregate = () => import('@/views/data_aggregate/index.vue')
const DataCleanse = () => import('@/views/data_cleanse/index.vue')
const AccessDashboard = () => import('@/views/access_dashboard/index.vue')
const SqlTemplate = () => import('@/views/sql_template/index.vue')
const ResultCache = () => import('@/views/result_cache/index.vue')
const QueryAudit = () => import('@/views/query_audit/index.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    { path: '/metric_domain', name: 'metric_domain', component: MetricDomain },
    { path: '/derived_metric', name: 'derived_metric', component: DerivedMetric },
    { path: '/api_service', name: 'api_service', component: ApiService },
    { path: '/query_optimize', name: 'query_optimize', component: QueryOptimize },
    { path: '/optimize_report', name: 'optimize_report', component: OptimizeReport },
    { path: '/plan_decision', name: 'plan_decision', component: PlanDecision },
    { path: '/api_subscribe', name: 'api_subscribe', component: ApiSubscribe },
    { path: '/call_credential', name: 'call_credential', component: CallCredential },
    { path: '/datasource_connect', name: 'datasource_connect', component: DatasourceConnect },
    { path: '/call_trace', name: 'call_trace', component: CallTrace },
    { path: '/data_preview', name: 'data_preview', component: DataPreview },
    { path: '/api_version', name: 'api_version', component: ApiVersion },
    { path: '/batch_export', name: 'batch_export', component: BatchExport },
    { path: '/metric_homonym', name: 'metric_homonym', component: MetricHomonym },
    { path: '/data_aggregate', name: 'data_aggregate', component: DataAggregate },
    { path: '/data_cleanse', name: 'data_cleanse', component: DataCleanse },
    { path: '/access_dashboard', name: 'access_dashboard', component: AccessDashboard },
    { path: '/sql_template', name: 'sql_template', component: SqlTemplate },
    { path: '/result_cache', name: 'result_cache', component: ResultCache },
    { path: '/query_audit', name: 'query_audit', component: QueryAudit },
  ],
})

export default router
