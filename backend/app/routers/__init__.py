"""业务模块路由汇总。

这里统一按别名导入再暴露 ROUTERS：模块名有可能和内置名撞车（某个业务模块就叫 dict、list
这种名字时），按名字直接 import 会把内置类型覆盖掉，函数注解在运行时求值就会报
'module' object is not subscriptable。
"""
from __future__ import annotations

from app.routers import metric_domain as router_metric_domain
from app.routers import derived_metric as router_derived_metric
from app.routers import api_service as router_api_service
from app.routers import query_optimize as router_query_optimize
from app.routers import api_subscribe as router_api_subscribe
from app.routers import call_credential as router_call_credential
from app.routers import datasource_connect as router_datasource_connect
from app.routers import call_trace as router_call_trace
from app.routers import data_preview as router_data_preview
from app.routers import api_version as router_api_version
from app.routers import batch_export as router_batch_export
from app.routers import metric_homonym as router_metric_homonym
from app.routers import data_aggregate as router_data_aggregate
from app.routers import data_cleanse as router_data_cleanse
from app.routers import access_dashboard as router_access_dashboard
from app.routers import sql_template as router_sql_template
from app.routers import result_cache as router_result_cache
from app.routers import query_audit as router_query_audit
from app.routers import optimize_report as router_optimize_report
from app.routers import plan_decision as router_plan_decision
from app.routers import chain as router_chain

ROUTERS = [router_metric_domain, router_derived_metric, router_api_service, router_query_optimize, router_optimize_report, router_plan_decision, router_api_subscribe, router_call_credential, router_datasource_connect, router_call_trace, router_data_preview, router_api_version, router_batch_export, router_metric_homonym, router_data_aggregate, router_data_cleanse, router_access_dashboard, router_sql_template, router_result_cache, router_query_audit, router_chain]
