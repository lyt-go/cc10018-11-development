"""执行计划视图接口：查询服务为已绑定请求选择计划，列出已采纳与回退的请求。"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas import ActionPayload, ActionResult, PageResult
from app.services.plan_decision import PlanDecisionService

router = APIRouter(prefix="/api/plan_decision", tags=["执行计划视图"])

service = PlanDecisionService()

LIST_FIELDS = ["决策编号", "关联接口", "请求类别", "决策结果", "扫描节点", "估算行数", "报告版本", "回退原因"]
STATUSES = ["待核对", "已核对", "已确认", "已归档"]


def query_filters(request: Request) -> dict[str, str]:
    """只接受当前模块声明过的字段，忽略分页等保留参数。"""
    return {
        key: value.strip()
        for key, value in request.query_params.items()
        if key in LIST_FIELDS and value.strip()
    }


@router.get("", response_model=PageResult[dict])
def list_entries(
    request: Request,
    keyword: str | None = Query(default=None, description="按决策编号检索"),
    status: str | None = Query(default=None, description="待核对、已核对、已确认、已归档"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> PageResult[dict]:
    """按页面字段、决策编号关键字与状态过滤执行计划决策列表。"""
    items, total = service.list_entries(
        filters=query_filters(request), keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(
    request: Request,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> StreamingResponse:
    """下载当前筛选条件下的 UTF-8 CSV；必须声明在 /{entry_id} 之前。"""
    items, _ = service.list_entries(
        filters=query_filters(request), keyword=keyword, status=status, page=1, size=1000000)
    output = io.StringIO()
    output.write("﻿")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["id", *LIST_FIELDS, "status"])
    for item in items:
        row = []
        for value in [item.get("id"), *(item.get(field, "") for field in LIST_FIELDS), item.get("status", "")]:
            text = "" if value is None else str(value)
            row.append("'" + text if text.startswith(("=", "+", "-", "@")) else text)
        writer.writerow(row)
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="plan_decision.csv"'})


@router.get("/summary")
def decision_summary(api_code: str | None = Query(default=None, description="按接口编号过滤")) -> dict:
    """按请求类别汇总实际使用的计划与成本：单日与整月查询的差异一眼可见。"""
    return service.summary(api_code or None)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条决策明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"执行计划决策 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: dict[str, object]) -> ActionResult:
    """登记一条执行计划决策，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="执行计划决策已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: ActionPayload) -> ActionResult:
    """对单条决策执行执行核对、确认采纳、归档记录；不允许的动作会被拦下并说明原因。"""
    entry, message = service.run_action(entry_id, payload.action.strip())
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/select")
def select_plan(payload: dict[str, object]) -> dict:
    """查询服务入口：按报告适用范围为本次已绑定的请求选择可执行计划。

    采纳的扫描节点或回退原因都关联到报告版本；参数为空或样本不足时
    保留原执行路径。决策结果写入执行计划视图。
    """
    api_id = payload.get("api_id")
    if api_id is None:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "api_id 必填"})
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "params 必须是对象"})
    result = service.select_plan(int(api_id), params)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result
