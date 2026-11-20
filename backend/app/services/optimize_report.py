"""优化分析报告业务规则：报告生成、版本管理、状态流转与适用范围判定。

报告是慢查询分析交付给查询服务的可执行产物：按实际绑定条件估算，
记录不同样本数据对应的执行计划、扫描节点和索引建议；未经验证的收益
只能标记为「待验证」，不写成已验证收益。
"""
from __future__ import annotations

import json
from typing import Any

from app.store import store
from app.engine.plan_estimator import build_bound_report

MODULE = "optimize_report"
LIST_FIELDS = ["报告编号", "关联接口", "报告版本", "样本范围", "适用条件", "索引建议", "收益核验", "优化状态"]
REQUIRED_FIELDS = ["报告编号", "关联接口", "报告版本"]
STATUS_ORDER = ["草稿", "分析中", "已发布", "已停用"]
ACTION_RULES = {"开始分析": "分析中", "发布报告": "已发布", "停用报告": "已停用"}
NEGATIVE_ACTIONS = ["停用报告"]

# 查询服务只采用「已发布」状态的报告版本。
ADOPTABLE_STATUS = "已发布"


class OptimizeReportService:
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
            rows = [row for row in rows if keyword.casefold() in str(row.get("报告编号", "")).casefold()]
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
        entry.setdefault("样本计划", "[]")
        entry.setdefault("索引建议明细", "[]")
        entry.setdefault("适用条件明细", "")
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"优化分析报告 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于优化分析报告可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["优化状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"优化分析报告已{action}"

    def generate(self, api_id: int) -> tuple[dict[str, Any] | None, str]:
        """按实际绑定条件为接口估算并生成新版本报告（生成即完成核对，直接发布）。"""
        api = store.find("api_service", api_id)
        if not api:
            return None, f"接口 {api_id} 不存在"

        content = build_bound_report(api)
        rows = store.rows(MODULE)
        entry_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        version_no = sum(1 for row in rows if row.get("关联接口") == api.get("接口编号")) + 1

        suggestions = content["索引建议"]
        idx_summary = "; ".join(
            f"{item['索引名']}({item['字段']}) {item['类型']} · {item['核验状态']}" for item in suggestions
        )
        entry = {
            "id": entry_id,
            "status": ADOPTABLE_STATUS,
            "pending": False,
            "abnormal": False,
            "报告编号": f"RPT-{entry_id:04d}",
            "关联接口": api.get("接口编号", ""),
            "报告版本": f"v{version_no}",
            "样本范围": content["样本范围"],
            "适用条件": content["适用条件"],
            "索引建议": idx_summary,
            "收益核验": content["收益核验"],
            "优化状态": ADOPTABLE_STATUS,
            "适用条件明细": json.dumps(content["适用条件明细"], ensure_ascii=False) if content["适用条件明细"] else "",
            "样本计划": json.dumps(content["样本计划"], ensure_ascii=False),
            "索引建议明细": json.dumps(suggestions, ensure_ascii=False),
        }
        rows.append(entry)
        return entry, f"报告 {entry['报告编号']}（{entry['报告版本']}）已生成并发布"

    def get_detail(self, entry_id: int) -> dict[str, Any] | None:
        """读取报告完整内容：样本计划、索引建议明细按 JSON 解析后返回。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        detail = dict(entry)
        for field in ("样本计划", "索引建议明细"):
            raw = entry.get(field) or "[]"
            try:
                detail[field] = json.loads(raw)
            except (TypeError, ValueError):
                detail[field] = []
        raw_scope = entry.get("适用条件明细") or ""
        try:
            detail["适用条件明细"] = json.loads(raw_scope) if raw_scope else None
        except (TypeError, ValueError):
            detail["适用条件明细"] = None
        return detail

    @staticmethod
    def latest_adoptable(api_code: str) -> dict[str, Any] | None:
        """查询服务视角：取接口最新一份已发布报告作为可采用版本。"""
        candidates = [
            row for row in store.rows(MODULE)
            if row.get("关联接口") == api_code and row.get("status") == ADOPTABLE_STATUS
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda row: int(row.get("id", 0)))
