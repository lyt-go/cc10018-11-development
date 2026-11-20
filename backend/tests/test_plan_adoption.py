"""查询优化分析报告与执行计划决策测试。

覆盖任务要求：
1. 报告按实际绑定条件估算，记录不同样本数据的执行计划、扫描节点和索引建议；
2. 建议不得改变查询返回行或字段（固定结果集核对）；
3. 参数为空或样本不足时保留原执行路径；
4. 未知收益不写成已验证收益；
5. 查询服务按报告适用范围选择计划，采纳节点或回退原因关联报告版本；
6. 执行计划视图列出已采纳与回退请求，展示实际扫描节点与估算行数；
7. 单日与整月两类请求的计划与成本都能被看到。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.store import store
from app.engine import plan_estimator as estimator
from app.services.optimize_report import OptimizeReportService
from app.services.plan_decision import PlanDecisionService

TRADE_API_ID = 6  # API-TRADE-002 交易地区日报查询
DAY_PARAMS = {"start_date": "2026-11-15", "end_date": "2026-11-15", "region_list": ["EAST", "NORTH"]}
MONTH_PARAMS = {"start_date": "2026-11-01", "end_date": "2026-11-30", "region_list": ["EAST", "NORTH"]}
OUT_OF_SAMPLE_PARAMS = {"start_date": "2026-12-01", "end_date": "2026-12-01", "region_list": ["EAST"]}


def reset_store():
    """重新加载seed数据。"""
    from app.seed import SEED_ROWS
    store._tables = {name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()}


def test_report_generation_records_sample_plans():
    """报告按实际绑定条件估算，记录不同样本数据对应的执行计划、扫描节点和索引建议。"""
    reset_store()
    service = OptimizeReportService()
    entry, message = service.generate(TRADE_API_ID)
    assert entry is not None, message
    assert entry["报告版本"] == "v2"  # 种子里已有 v1，新生成的递增
    assert entry["status"] == "已发布"
    assert entry["收益核验"] == "已验证"
    assert entry["适用条件"] == "date_span_days<=7 且地区条件齐备"

    detail = service.get_detail(entry["id"])
    classes = {item["样本类别"]: item for item in detail["样本计划"]}
    assert set(classes) == {"单日查询", "一周查询", "整月查询"}

    # 每个样本都记录了两种计划的扫描节点与估算行数
    day = classes["单日查询"]
    assert day["plans"][0]["scan_node"] == estimator.SEQ_SCAN_NODE
    assert day["plans"][1]["scan_node"] == estimator.IDX_SCAN_NODE
    assert day["plans"][1]["scan_rows"] < day["plans"][0]["scan_rows"]
    assert day["采用计划"] == estimator.IDX_PLAN_KEY

    # 整月样本：索引路径反而扩大扫描，结论保留原执行路径
    month = classes["整月查询"]
    assert month["plans"][1]["scan_rows"] > month["plans"][0]["scan_rows"]
    assert month["采用计划"] == estimator.SEQ_PLAN_KEY
    assert "保留原执行路径" in month["结论"]

    # 索引建议带适用范围与风险提示，不把整月场景写进收益
    suggestion = detail["索引建议明细"][0]
    assert suggestion["核验状态"] == "已验证"
    assert "date_span_days<=7" in suggestion["适用条件"]
    assert "整月" in suggestion["风险提示"]
    print("  [PASS] 报告按绑定条件估算并记录样本计划")


def test_unknown_benefit_not_marked_verified():
    """样本不足时索引建议只能标「待验证」，未知收益不写成已验证收益。"""
    reset_store()
    service = OptimizeReportService()
    # API-LOGIS-001（id=5）的表不在样本库覆盖范围内
    entry, message = service.generate(5)
    assert entry is not None, message
    assert entry["收益核验"] == "待验证"
    assert entry["样本范围"] == "无（样本不足）"

    detail = service.get_detail(entry["id"])
    suggestion = detail["索引建议明细"][0]
    assert suggestion["核验状态"] == "待验证"
    assert "未知" in suggestion["预期收益"]
    assert "已验证" not in suggestion["预期收益"]
    assert detail["适用条件明细"] is None
    print("  [PASS] 未知收益不写成已验证收益")


def test_select_plan_adopts_index_for_single_day():
    """单日请求在报告适用范围内：采纳索引路径，扫描节点关联报告版本。"""
    reset_store()
    service = PlanDecisionService()
    result = service.select_plan(TRADE_API_ID, DAY_PARAMS)
    assert result["ok"]
    decision = result["decision"]
    assert decision["决策结果"] == "已采纳"
    assert decision["请求类别"] == "单日查询"
    assert decision["扫描节点"] == estimator.IDX_SCAN_NODE
    assert decision["报告版本"] == "v1"  # 关联到种子报告版本
    assert decision["回退原因"] == ""
    assert int(decision["估算行数"]) > 0
    assert "核对一致" in decision["结果核对"]
    # 决策已写入执行计划视图
    stored = store.find("plan_decision", decision["id"])
    assert stored is not None and stored["扫描节点"] == estimator.IDX_SCAN_NODE
    print("  [PASS] 单日请求采纳索引路径并关联报告版本")


def test_select_plan_falls_back_for_full_month():
    """整月请求超出报告适用范围：回退并保留原执行路径，回退原因关联报告版本。"""
    reset_store()
    service = PlanDecisionService()
    result = service.select_plan(TRADE_API_ID, MONTH_PARAMS)
    assert result["ok"]
    decision = result["decision"]
    assert decision["决策结果"] == "已回退"
    assert decision["请求类别"] == "整月查询"
    assert decision["扫描节点"] == estimator.SEQ_SCAN_NODE
    assert decision["报告版本"] == "v1"  # 回退原因同样关联报告版本
    assert "超出报告适用范围" in decision["回退原因"]
    assert "保留原执行路径" in decision["回退原因"]
    # 回退后展示的估算行数就是原执行路径的扫描行数
    est = estimator.estimate_plans(
        estimator.date(2026, 11, 1), estimator.date(2026, 11, 30), ["EAST", "NORTH"])
    assert decision["估算行数"] == str(est["plans"][0]["scan_rows"])
    print("  [PASS] 整月请求回退原路径并关联报告版本")


def test_select_plan_keeps_original_when_params_empty():
    """参数为空时必须保留原执行路径。"""
    reset_store()
    service = PlanDecisionService()
    for params in ({}, {"start_date": "2026-11-15"}, {"start_date": "2026-11-15", "end_date": "2026-11-15", "region_list": []}):
        result = service.select_plan(TRADE_API_ID, params)
        assert result["ok"]
        decision = result["decision"]
        assert decision["决策结果"] == "已回退"
        assert decision["扫描节点"] == estimator.SEQ_SCAN_NODE
        assert "参数为空" in decision["回退原因"]
        assert "保留原执行路径" in decision["回退原因"]
        assert decision["估算行数"] == "—"
    print("  [PASS] 参数为空保留原执行路径")


def test_select_plan_keeps_original_when_sample_insufficient():
    """样本不足时必须保留原执行路径。"""
    reset_store()
    service = PlanDecisionService()
    result = service.select_plan(TRADE_API_ID, OUT_OF_SAMPLE_PARAMS)
    assert result["ok"]
    decision = result["decision"]
    assert decision["决策结果"] == "已回退"
    assert decision["请求类别"] == "样本不足"
    assert decision["扫描节点"] == estimator.SEQ_SCAN_NODE
    assert "样本不足" in decision["回退原因"]
    assert "保留原执行路径" in decision["回退原因"]
    assert "未核对" in decision["结果核对"]
    print("  [PASS] 样本不足保留原执行路径")


def test_fixed_result_set_verification():
    """用固定结果集核对一天、整月和样本不足的请求，比较结果行及字段和扫描节点差异。"""
    reset_store()
    service = PlanDecisionService()

    day = service.select_plan(TRADE_API_ID, DAY_PARAMS)["decision"]
    month = service.select_plan(TRADE_API_ID, MONTH_PARAMS)["decision"]
    lack = service.select_plan(TRADE_API_ID, OUT_OF_SAMPLE_PARAMS)["decision"]

    # 单日与整月：两种计划返回行与字段一致，扫描节点不同
    for decision in (day, month):
        assert "核对一致" in decision["结果核对"]
        assert "dt,region,gmv" in decision["结果核对"]
    assert day["扫描节点"] != month["扫描节点"]

    # 样本不足：不生成对比计划，保留原路径
    assert "未核对" in lack["结果核对"]
    assert lack["扫描节点"] == estimator.SEQ_SCAN_NODE

    # 直接在引擎层核对：两种计划的结果行与字段完全一致
    for params in (DAY_PARAMS, MONTH_PARAMS):
        parsed = estimator.parse_bound_params(params)
        verify = estimator.verify_fixed_result_set(parsed["start"], parsed["end"], parsed["regions"])
        assert verify["consistent"]
        assert verify["fields"] == ["dt", "region", "gmv"]
        assert verify["seq_rows"] == verify["idx_rows"] == verify["result_rows"]
    print("  [PASS] 固定结果集核对三类请求")


def test_adopted_plan_does_not_change_result_rows_or_fields():
    """被采纳的建议不得改变查询返回行或字段。"""
    reset_store()
    parsed = estimator.parse_bound_params(DAY_PARAMS)
    verify = estimator.verify_fixed_result_set(parsed["start"], parsed["end"], parsed["regions"])
    assert verify["consistent"]
    # 固定结果集的行内容逐行一致（不仅是行数）
    start_text, end_text = parsed["start"].isoformat(), parsed["end"].isoformat()
    region_set = set(parsed["regions"])
    seq_out = sorted(
        (row["dt"], row["region"], row["gmv"]) for row in estimator.FIXED_ROWS
        if start_text <= row["dt"] <= end_text and row["region"] in region_set)
    idx_out = sorted(
        (row["dt"], row["region"], row["gmv"]) for row in estimator.FIXED_ROWS
        if row["region"] in region_set and start_text <= row["dt"] <= end_text)
    assert seq_out == idx_out
    assert len(seq_out) == verify["result_rows"] > 0
    print("  [PASS] 采纳建议不改变返回行或字段")


def test_plan_view_lists_adopted_and_fallback_with_scan_nodes():
    """执行计划视图列出已采纳与回退的请求，展示实际扫描节点与估算行数。"""
    reset_store()
    service = PlanDecisionService()
    service.select_plan(TRADE_API_ID, DAY_PARAMS)
    service.select_plan(TRADE_API_ID, MONTH_PARAMS)

    items, total = service.list_entries(filters={"关联接口": "API-TRADE-002"}, size=100)
    assert total >= 2
    adopted = [row for row in items if row["决策结果"] == "已采纳"]
    fallback = [row for row in items if row["决策结果"] == "已回退"]
    assert adopted and fallback
    for row in items:
        assert row["扫描节点"]  # 实际扫描节点已展示
        assert row["估算行数"]  # 估算行数已展示
    assert any(row["扫描节点"] == estimator.IDX_SCAN_NODE for row in adopted)
    assert any(row["扫描节点"] == estimator.SEQ_SCAN_NODE for row in fallback)
    # 已采纳与已回退都可按决策结果筛选
    adopted_only, _ = service.list_entries(filters={"决策结果": "已采纳"}, size=100)
    assert all(row["决策结果"] == "已采纳" for row in adopted_only)
    print("  [PASS] 执行计划视图列出采纳与回退请求")


def test_summary_shows_both_request_classes():
    """领取报表的人能看到单日与整月两类查询实际使用的计划和成本。"""
    reset_store()
    service = PlanDecisionService()
    service.select_plan(TRADE_API_ID, DAY_PARAMS)
    service.select_plan(TRADE_API_ID, MONTH_PARAMS)

    summary = service.summary("API-TRADE-002")
    assert summary["ok"]
    classes = {item["请求类别"]: item for item in summary["classes"]}
    assert "单日查询" in classes and "整月查询" in classes
    day_class = classes["单日查询"]
    month_class = classes["整月查询"]
    assert day_class["已采纳"] >= 1
    assert month_class["已回退"] >= 1
    assert estimator.IDX_SCAN_NODE in day_class["实际扫描节点"]
    assert estimator.SEQ_SCAN_NODE in month_class["实际扫描节点"]
    # 两类查询的成本差异可见：整月成本远高于单日
    assert month_class["平均估算成本"] > day_class["平均估算成本"]
    print("  [PASS] 汇总展示两类查询的计划与成本")


def test_http_endpoints():
    """通过 TestClient 验证报告与决策的 HTTP 端点。"""
    reset_store()
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # 报告列表与详情
    resp = client.get("/api/optimize_report")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 3
    resp = client.get("/api/optimize_report/1/detail")
    assert resp.status_code == 200
    detail = resp.json()["detail"]
    assert detail["报告版本"] == "v1"
    assert len(detail["样本计划"]) == 3
    assert detail["适用条件明细"]["max_date_span_days"] == 7

    # 生成新版本报告
    resp = client.post("/api/optimize_report/generate", json={"api_id": TRADE_API_ID})
    assert resp.status_code == 200
    assert resp.json()["entry"]["报告版本"] == "v2"
    assert resp.json()["entry"]["收益核验"] == "已验证"

    # 计划选择：单日采纳（关联最新报告 v2）
    resp = client.post("/api/plan_decision/select", json={"api_id": TRADE_API_ID, "params": DAY_PARAMS})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"]["决策结果"] == "已采纳"
    assert body["decision"]["报告版本"] == "v2"
    assert body["report"]["适用条件"] == "date_span_days<=7 且地区条件齐备"

    # 计划选择：整月回退
    resp = client.post("/api/plan_decision/select", json={"api_id": TRADE_API_ID, "params": MONTH_PARAMS})
    assert resp.status_code == 200
    assert resp.json()["decision"]["决策结果"] == "已回退"

    # 计划选择：参数为空回退
    resp = client.post("/api/plan_decision/select", json={"api_id": TRADE_API_ID, "params": {}})
    assert resp.status_code == 200
    assert "参数为空" in resp.json()["decision"]["回退原因"]

    # 执行计划视图：列表与汇总
    resp = client.get("/api/plan_decision", params={"决策结果": "已采纳"})
    assert resp.status_code == 200
    assert all(item["决策结果"] == "已采纳" for item in resp.json()["items"])
    resp = client.get("/api/plan_decision/summary", params={"api_code": "API-TRADE-002"})
    assert resp.status_code == 200
    classes = {item["请求类别"] for item in resp.json()["classes"]}
    assert {"单日查询", "整月查询"} <= classes

    # 导出
    resp = client.get("/api/optimize_report/export")
    assert resp.status_code == 200
    assert "optimize_report.csv" in resp.headers["content-disposition"]
    resp = client.get("/api/plan_decision/export")
    assert resp.status_code == 200
    assert "plan_decision.csv" in resp.headers["content-disposition"]
    print("  [PASS] HTTP 端点")


def run_all():
    print("\n=== 开始查询优化报告与计划决策测试 ===")
    tests = [
        test_report_generation_records_sample_plans,
        test_unknown_benefit_not_marked_verified,
        test_select_plan_adopts_index_for_single_day,
        test_select_plan_falls_back_for_full_month,
        test_select_plan_keeps_original_when_params_empty,
        test_select_plan_keeps_original_when_sample_insufficient,
        test_fixed_result_set_verification,
        test_adopted_plan_does_not_change_result_rows_or_fields,
        test_plan_view_lists_adopted_and_fallback_with_scan_nodes,
        test_summary_shows_both_request_classes,
        test_http_endpoints,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [FAIL] {test.__name__}: {exc}")
            failed += 1
    print(f"\n=== 测试结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 项 ===")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
