"""执行计划决策业务规则：查询服务按报告适用范围为已绑定请求选择可执行计划。

决策约束：
1. 只采用「已发布」报告版本，采纳的扫描节点或回退原因都关联到报告版本；
2. 参数为空或样本不足时保留原执行路径，不生成新计划；
3. 采纳前用固定结果集核对，建议不得改变查询返回行或字段；
4. 每次决策写入执行计划视图，展示实际扫描节点与估算行数。
"""
from __future__ import annotations

import json
from typing import Any

from app.store import store
from app.engine import plan_estimator as estimator
from app.services.optimize_report import OptimizeReportService

MODULE = "plan_decision"
LIST_FIELDS = ["决策编号", "关联接口", "请求类别", "决策结果", "扫描节点", "估算行数", "报告版本", "回退原因"]
REQUIRED_FIELDS = ["决策编号", "关联接口", "请求类别"]
STATUS_ORDER = ["待核对", "已核对", "已确认", "已归档"]
ACTION_RULES = {"执行核对": "已核对", "确认采纳": "已确认", "归档记录": "已归档"}
NEGATIVE_ACTIONS = ["归档记录"]

ADOPTED = "已采纳"
FELL_BACK = "已回退"


class PlanDecisionService:
    def list_entries(
        self,
        *,
        filters: dict[str, str] | None = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        for field, expected in (filters or {}).items():
            rows = [row for row in rows if expected.casefold() in str(row.get(field, "")).casefold()]
        if keyword:
            rows = [row for row in rows if keyword.casefold() in str(row.get("决策编号", "")).casefold()]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = (page - 1) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in LIST_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"执行计划决策 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于执行计划决策可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"执行计划决策已{action}"

    # ───────────────────────────────────────────────
    # 查询服务计划选择
    # ───────────────────────────────────────────────
    def select_plan(self, api_id: int, params: dict[str, Any]) -> dict[str, Any]:
        """为本次已绑定的请求选择可执行计划，并把决策写入执行计划视图。"""
        api = store.find("api_service", api_id)
        if not api:
            return {"ok": False, "error": f"接口 {api_id} 不存在"}
        api_code = api.get("接口编号", "")

        report = OptimizeReportService.latest_adoptable(api_code)
        report_version = report.get("报告版本", "") if report else ""
        bound_text = self._format_bound(params)

        # 1. 参数为空或非法：保留原执行路径，不做任何估算。
        parsed = estimator.parse_bound_params(params)
        if not parsed.get("ok"):
            reason = parsed["reason"]
            return self._record(
                api_code=api_code, request_class="参数为空" if "为空" in reason else "参数非法",
                bound_text=bound_text, result=FELL_BACK,
                scan_node=estimator.SEQ_SCAN_NODE, est_rows="—", est_cost="—",
                report_version=report_version or "—",
                fallback=f"{reason}，保留原执行路径",
                verify_text="未核对（参数未绑定，不生成对比计划）",
                plans=None, report=report,
            )

        start, end, regions = parsed["start"], parsed["end"], parsed["regions"]
        span_days = (end - start).days + 1
        request_class = estimator.classify_request(span_days)

        # 2. 样本不足：保留原执行路径。
        est = estimator.estimate_plans(start, end, regions)
        if not est.get("sufficient"):
            return self._record(
                api_code=api_code, request_class="样本不足",
                bound_text=bound_text, result=FELL_BACK,
                scan_node=estimator.SEQ_SCAN_NODE, est_rows="—", est_cost="—",
                report_version=report_version or "—",
                fallback=f"{est['reason']}，保留原执行路径",
                verify_text="未核对（样本不足，未生成对比计划）",
                plans=None, report=report,
            )

        seq_plan, idx_plan = est["plans"]

        # 3. 无已发布报告：保留原执行路径。
        if report is None:
            return self._record(
                api_code=api_code, request_class=request_class,
                bound_text=bound_text, result=FELL_BACK,
                scan_node=seq_plan["scan_node"], est_rows=str(seq_plan["scan_rows"]),
                est_cost=str(seq_plan["est_cost"]), report_version="—",
                fallback="无已发布的优化分析报告，保留原执行路径",
                verify_text="未核对（无可用报告版本）",
                plans=est["plans"], report=None,
            )

        # 4. 超出报告适用范围：保留原执行路径，回退原因关联报告版本。
        scope = self._parse_scope(report)
        if scope is None:
            return self._record(
                api_code=api_code, request_class=request_class,
                bound_text=bound_text, result=FELL_BACK,
                scan_node=seq_plan["scan_node"], est_rows=str(seq_plan["scan_rows"]),
                est_cost=str(seq_plan["est_cost"]), report_version=report_version,
                fallback="报告未给出可采用的适用范围，保留原执行路径",
                verify_text="未核对（报告收益未验证）",
                plans=est["plans"], report=report,
            )
        if span_days > int(scope.get("max_date_span_days", 0)) or (scope.get("require_region") and not regions):
            return self._record(
                api_code=api_code, request_class=request_class,
                bound_text=bound_text, result=FELL_BACK,
                scan_node=seq_plan["scan_node"], est_rows=str(seq_plan["scan_rows"]),
                est_cost=str(seq_plan["est_cost"]), report_version=report_version,
                fallback=(
                    f"超出报告适用范围（date_span={span_days} > {scope['max_date_span_days']}），保留原执行路径"
                ),
                verify_text=self._verify_text(start, end, regions),
                plans=est["plans"], report=report,
            )

        # 5. 固定结果集核对：建议不得改变查询返回行或字段，不一致则回退。
        verify = estimator.verify_fixed_result_set(start, end, regions)
        if not verify["consistent"]:
            return self._record(
                api_code=api_code, request_class=request_class,
                bound_text=bound_text, result=FELL_BACK,
                scan_node=seq_plan["scan_node"], est_rows=str(seq_plan["scan_rows"]),
                est_cost=str(seq_plan["est_cost"]), report_version=report_version,
                fallback=f"结果集核对不一致（{verify['summary']}），保留原执行路径",
                verify_text=verify["summary"],
                plans=est["plans"], report=report,
            )

        # 6. 采纳报告索引路径。
        return self._record(
            api_code=api_code, request_class=request_class,
            bound_text=bound_text, result=ADOPTED,
            scan_node=idx_plan["scan_node"], est_rows=str(idx_plan["scan_rows"]),
            est_cost=str(idx_plan["est_cost"]), report_version=report_version,
            fallback="",
            verify_text=verify["summary"],
            plans=est["plans"], report=report,
        )

    def summary(self, api_code: str | None = None) -> dict[str, Any]:
        """按请求类别汇总实际使用的计划与成本，供领取报表的人查看两类查询差异。"""
        rows = store.rows(MODULE)
        if api_code:
            rows = [row for row in rows if row.get("关联接口") == api_code]
        classes: dict[str, dict[str, Any]] = {}
        for row in rows:
            bucket = classes.setdefault(row.get("请求类别", "未分类"), {
                "请求类别": row.get("请求类别", "未分类"),
                "决策数": 0, "已采纳": 0, "已回退": 0,
                "扫描节点": set(), "估算行数样本": [], "估算成本样本": [],
            })
            bucket["决策数"] += 1
            if row.get("决策结果") == ADOPTED:
                bucket["已采纳"] += 1
            elif row.get("决策结果") == FELL_BACK:
                bucket["已回退"] += 1
            node = str(row.get("扫描节点", ""))
            if node:
                bucket["扫描节点"].add(node)
            for field, key in (("估算行数", "估算行数样本"), ("估算成本", "估算成本样本")):
                try:
                    bucket[key].append(float(row.get(field, "")))
                except (TypeError, ValueError):
                    continue
        items = []
        for bucket in classes.values():
            items.append({
                "请求类别": bucket["请求类别"],
                "决策数": bucket["决策数"],
                "已采纳": bucket["已采纳"],
                "已回退": bucket["已回退"],
                "实际扫描节点": sorted(bucket["扫描节点"]),
                "平均估算行数": round(sum(bucket["估算行数样本"]) / len(bucket["估算行数样本"]), 1) if bucket["估算行数样本"] else None,
                "平均估算成本": round(sum(bucket["估算成本样本"]) / len(bucket["估算成本样本"]), 1) if bucket["估算成本样本"] else None,
            })
        items.sort(key=lambda item: item["请求类别"])
        return {"ok": True, "api_code": api_code or "", "classes": items}

    # ───────────────────────────────────────────────
    # 内部工具
    # ───────────────────────────────────────────────
    def _record(
        self,
        *,
        api_code: str,
        request_class: str,
        bound_text: str,
        result: str,
        scan_node: str,
        est_rows: str,
        est_cost: str,
        report_version: str,
        fallback: str,
        verify_text: str,
        plans: list[dict[str, Any]] | None,
        report: dict[str, Any] | None,
    ) -> dict[str, Any]:
        rows = store.rows(MODULE)
        entry_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        entry = {
            "id": entry_id,
            "status": "已核对",
            "pending": True,
            "abnormal": False,
            "决策编号": f"DEC-{entry_id:04d}",
            "关联接口": api_code,
            "请求类别": request_class,
            "绑定条件": bound_text,
            "决策结果": result,
            "扫描节点": scan_node,
            "估算行数": est_rows,
            "估算成本": est_cost,
            "报告版本": report_version,
            "回退原因": fallback,
            "结果核对": verify_text,
        }
        rows.append(entry)
        return {
            "ok": True,
            "decision": entry,
            "plans": plans or [],
            "report": (
                {"报告编号": report.get("报告编号"), "报告版本": report.get("报告版本"),
                 "适用条件": report.get("适用条件")}
                if report else None
            ),
        }

    @staticmethod
    def _format_bound(params: dict[str, Any]) -> str:
        if not params:
            return ""
        parts = []
        for key in ("start_date", "end_date", "region_list"):
            value = params.get(key)
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                value = ",".join(str(item) for item in value)
            parts.append(f"{key}={value}")
        return ",".join(parts)

    @staticmethod
    def _parse_scope(report: dict[str, Any]) -> dict[str, Any] | None:
        raw = report.get("适用条件明细") or ""
        if not raw:
            return None
        try:
            scope = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not isinstance(scope, dict) or not scope.get("max_date_span_days"):
            return None
        return scope

    @staticmethod
    def _verify_text(start: Any, end: Any, regions: list[str]) -> str:
        verify = estimator.verify_fixed_result_set(start, end, regions)
        return verify["summary"]
