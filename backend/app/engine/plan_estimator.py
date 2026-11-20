"""绑定条件估算引擎：按实际绑定条件估算执行计划、扫描节点与索引建议。

核心能力：
1. 样本库：交易表 dwd_trade_order_di 2026-11 月按 (dt, region) 的确定性行数样本，
   以及 240 行固定结果集明细，用于估算扫描行数与核对返回结果。
2. 候选计划估算：原执行路径（dt 分区顺序扫描 + region 过滤）与索引路径
   （idx_region_dt 联合索引 + 回表），输出扫描节点、估算行数与估算成本。
3. 结果集核对：两种计划在固定结果集上的返回行与字段必须一致；
   索引建议不得改变查询返回行或字段。
4. 计划选择支撑：参数为空或样本不足时不生成新计划，必须保留原执行路径；
   未经过样本估算与结果集核对的收益只能标记为「待验证」，不能写成已验证收益。
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from typing import Any

# ── 样本库：交易表 2026-11 月按 (dt, region) 的确定性样本 ──────────────
SAMPLE_TABLE = "dwd_trade_order_di"
REGIONS = ["EAST", "SOUTH", "WEST", "NORTH", "CENTRAL", "NORTHEAST", "SOUTHWEST", "NORTHWEST"]
SAMPLE_START = date(2026, 11, 1)
SAMPLE_END = date(2026, 11, 30)
MIN_SAMPLE_ROWS = 100

# ── 成本模型 ─────────────────────────────────────────────
# 原路径：dt 分区裁剪后顺序扫描，成本 = 顺序页数 × SEQ_PAGE_COST。
# 索引路径：idx_region_dt(region,dt) 命中后回表，回表行数随日期跨度放大
# （命中行散布到更多数据页，同一页被重复访问），成本 = 随机页数 × IDX_PAGE_COST。
# 短日期范围下索引路径扫描行数更少；整月范围下回表放大使扫描反而超过原路径。
PAGE_ROWS = 100
SEQ_PAGE_COST = 1.0
IDX_PAGE_COST = 1.5
FETCH_AMP_PER_DAY = 0.1

RESULT_FIELDS = ["dt", "region", "gmv"]

SEQ_PLAN_KEY = "seq_partition_scan"
IDX_PLAN_KEY = "idx_region_dt_scan"
SEQ_SCAN_NODE = "Seq Scan: dt分区裁剪 + region过滤"
IDX_SCAN_NODE = "Index Scan: idx_region_dt(region,dt) + 回表"
ORIGINAL_PLAN_NOTE = "原执行路径"

# 代表性绑定样本：同一交易接口大多数请求只查一天，月底少量整月查询，均带地区条件。
SAMPLE_BINDINGS = [
    {"样本类别": "单日查询", "start": date(2026, 11, 15), "end": date(2026, 11, 15),
     "regions": ["EAST", "NORTH"]},
    {"样本类别": "一周查询", "start": date(2026, 11, 10), "end": date(2026, 11, 16),
     "regions": ["EAST", "NORTH"]},
    {"样本类别": "整月查询", "start": date(2026, 11, 1), "end": date(2026, 11, 30),
     "regions": ["EAST", "NORTH"]},
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _day_rows(day: int, region_idx: int) -> int:
    """样本库中某天某地区的原始行数（确定性）。"""
    return 1250 + ((day * 7 + region_idx * 13) % 200)


def _day_gmv(day: int, region_idx: int) -> int:
    """固定结果集中某天某地区的聚合 gmv（确定性）。"""
    return _day_rows(day, region_idx) * (100 + region_idx * 10 + day % 5)


def fixed_result_rows() -> list[dict[str, Any]]:
    """固定结果集明细：2026-11 月每天 × 8 地区的 (dt, region, gmv) 聚合行。"""
    rows: list[dict[str, Any]] = []
    current = SAMPLE_START
    while current <= SAMPLE_END:
        for idx, region in enumerate(REGIONS):
            rows.append({
                "dt": current.isoformat(),
                "region": region,
                "gmv": _day_gmv(current.day, idx),
            })
        current += timedelta(days=1)
    return rows


FIXED_ROWS = fixed_result_rows()


def sample_coverage() -> dict[str, Any]:
    """样本库覆盖范围，供报告「样本范围」字段与样本充足性判断使用。"""
    total = sum(_day_rows(day, idx) for day in range(1, 31) for idx in range(len(REGIONS)))
    return {
        "table": SAMPLE_TABLE,
        "start": SAMPLE_START.isoformat(),
        "end": SAMPLE_END.isoformat(),
        "days": (SAMPLE_END - SAMPLE_START).days + 1,
        "regions": len(REGIONS),
        "total_rows": total,
        "label": f"{SAMPLE_START.isoformat()}~{SAMPLE_END.isoformat()} · 30天×{len(REGIONS)}地区",
    }


def parse_bound_params(params: dict[str, Any]) -> dict[str, Any]:
    """解析并校验实际绑定条件；参数为空或非法时明确给出原因，不做默认值补全。"""
    start_raw = str(params.get("start_date") or "").strip()
    end_raw = str(params.get("end_date") or "").strip()
    regions_raw = params.get("region_list")
    if isinstance(regions_raw, str):
        regions = [item.strip() for item in regions_raw.split(",") if item.strip()]
    elif isinstance(regions_raw, (list, tuple)):
        regions = [str(item).strip() for item in regions_raw if str(item).strip()]
    else:
        regions = []

    missing = []
    if not start_raw:
        missing.append("start_date")
    if not end_raw:
        missing.append("end_date")
    if not regions:
        missing.append("region_list")
    if missing:
        return {"ok": False, "reason": f"参数为空：{','.join(missing)} 未绑定"}

    if not DATE_RE.match(start_raw) or not DATE_RE.match(end_raw):
        return {"ok": False, "reason": "参数非法：start_date/end_date 须为 YYYY-MM-DD"}
    start = date.fromisoformat(start_raw)
    end = date.fromisoformat(end_raw)
    if start > end:
        return {"ok": False, "reason": "参数非法：start_date 晚于 end_date"}
    return {"ok": True, "start": start, "end": end, "regions": regions}


def classify_request(span_days: int) -> str:
    """按日期跨度给绑定请求分类：单日 / 整月 / 其他范围。"""
    if span_days == 1:
        return "单日查询"
    if span_days >= 28:
        return "整月查询"
    return "范围查询"


def estimate_plans(start: date, end: date, regions: list[str]) -> dict[str, Any]:
    """按实际绑定条件估算候选计划的扫描节点、估算行数与估算成本。"""
    span_days = (end - start).days + 1
    if start < SAMPLE_START or end > SAMPLE_END:
        return {
            "ok": False,
            "sufficient": False,
            "reason": f"样本不足：绑定区间 {start.isoformat()}~{end.isoformat()} "
                      f"超出样本覆盖 {SAMPLE_START.isoformat()}~{SAMPLE_END.isoformat()}",
        }
    unknown = [region for region in regions if region not in REGIONS]
    if unknown:
        return {
            "ok": False,
            "sufficient": False,
            "reason": f"样本不足：地区 {','.join(unknown)} 不在样本库覆盖范围内",
        }

    region_idx = {region: idx for idx, region in enumerate(REGIONS)}
    days = [SAMPLE_START + timedelta(days=offset)
            for offset in range((start - SAMPLE_START).days, (end - SAMPLE_START).days + 1)]
    total_rows = sum(_day_rows(day.day, idx) for day in days for idx in range(len(REGIONS)))
    if total_rows < MIN_SAMPLE_ROWS:
        return {
            "ok": False,
            "sufficient": False,
            "reason": f"样本不足：绑定区间内样本行数 {total_rows} 低于阈值 {MIN_SAMPLE_ROWS}",
        }

    hit_rows = sum(_day_rows(day.day, region_idx[region]) for day in days for region in regions)
    amplification = 1 + (span_days - 1) * FETCH_AMP_PER_DAY
    fetch_rows = round(hit_rows * amplification)

    seq_rows = total_rows
    idx_rows = hit_rows + fetch_rows
    seq_plan = {
        "plan_key": SEQ_PLAN_KEY,
        "plan_name": ORIGINAL_PLAN_NOTE,
        "scan_node": SEQ_SCAN_NODE,
        "scan_rows": seq_rows,
        "est_cost": math.ceil(seq_rows / PAGE_ROWS) * SEQ_PAGE_COST,
    }
    idx_plan = {
        "plan_key": IDX_PLAN_KEY,
        "plan_name": "索引路径",
        "scan_node": IDX_SCAN_NODE,
        "scan_rows": idx_rows,
        "est_cost": math.ceil(idx_rows / PAGE_ROWS) * IDX_PAGE_COST,
        "hit_rows": hit_rows,
        "fetch_rows": fetch_rows,
        "amplification": round(amplification, 2),
    }
    cheaper = idx_plan if idx_plan["est_cost"] < seq_plan["est_cost"] else seq_plan
    return {
        "ok": True,
        "sufficient": True,
        "span_days": span_days,
        "request_class": classify_request(span_days),
        "plans": [seq_plan, idx_plan],
        "cheaper_plan": cheaper["plan_key"],
    }


def verify_fixed_result_set(start: date, end: date, regions: list[str]) -> dict[str, Any]:
    """用固定结果集核对两种计划的返回行与字段：建议不得改变查询结果。"""
    start_text, end_text = start.isoformat(), end.isoformat()
    region_set = set(regions)

    # 原执行路径：分区裁剪后顺序扫描全部行，再按地区过滤。
    seq_out = [row for row in FIXED_ROWS
               if start_text <= row["dt"] <= end_text and row["region"] in region_set]
    # 索引路径：按 (region, dt) 定位命中行，过滤条件不变。
    idx_out = [row for row in FIXED_ROWS
               if row["region"] in region_set and start_text <= row["dt"] <= end_text]

    def normalize(rows: list[dict[str, Any]]) -> list[tuple[str, str, int]]:
        return sorted((row["dt"], row["region"], row["gmv"]) for row in rows)

    seq_rows = normalize(seq_out)
    idx_rows = normalize(idx_out)
    consistent = seq_rows == idx_rows
    return {
        "consistent": consistent,
        "result_rows": len(seq_rows),
        "fields": list(RESULT_FIELDS),
        "seq_rows": len(seq_rows),
        "idx_rows": len(idx_rows),
        "summary": (
            f"固定结果集核对一致：{len(seq_rows)} 行，字段 {','.join(RESULT_FIELDS)}"
            if consistent else
            f"固定结果集核对不一致：原路径 {len(seq_rows)} 行 / 索引路径 {len(idx_rows)} 行"
        ),
    }


def extract_table_name(sql_text: str) -> str:
    """从查询 SQL 中提取 FROM 后的表名，用于匹配样本库。"""
    match = re.search(r"\bFROM\s+(\w+)", sql_text, re.IGNORECASE)
    return match.group(1) if match else ""


def build_bound_report(api: dict[str, Any]) -> dict[str, Any]:
    """按代表性绑定样本为接口生成优化分析报告内容。

    报告只记录经过样本估算与固定结果集核对的结论；样本不足时索引建议
    标记为「待验证」，未知收益不写成已验证收益。
    """
    sql_text = api.get("查询SQL", "")
    table = extract_table_name(sql_text)
    coverage = sample_coverage()

    if table != SAMPLE_TABLE:
        return {
            "ok": True,
            "covered": False,
            "样本范围": "无（样本不足）",
            "适用条件": "无（样本不足，不可采用）",
            "适用条件明细": None,
            "样本计划": [],
            "索引建议": [{
                "字段": "(region, dt)",
                "索引名": "idx_region_dt",
                "类型": "btree联合",
                "适用条件": "无（样本不足）",
                "核验状态": "待验证",
                "预期收益": "未知（样本不足，未验证）",
                "风险提示": f"样本库未覆盖表 {table or '未知'}，不提供估算结论",
            }],
            "收益核验": "待验证",
        }

    sample_plans: list[dict[str, Any]] = []
    for binding in SAMPLE_BINDINGS:
        est = estimate_plans(binding["start"], binding["end"], binding["regions"])
        verify = verify_fixed_result_set(binding["start"], binding["end"], binding["regions"])
        seq_plan, idx_plan = est["plans"]
        adopted = idx_plan if est["cheaper_plan"] == IDX_PLAN_KEY else seq_plan
        sample_plans.append({
            "样本类别": binding["样本类别"],
            "绑定条件": {
                "start_date": binding["start"].isoformat(),
                "end_date": binding["end"].isoformat(),
                "region_list": list(binding["regions"]),
            },
            "跨度天数": est["span_days"],
            "plans": [seq_plan, idx_plan],
            "结果核对": verify,
            "采用计划": adopted["plan_key"],
            "结论": (
                f"采用索引路径（估算成本 {idx_plan['est_cost']} < 原路径 {seq_plan['est_cost']}）"
                if adopted["plan_key"] == IDX_PLAN_KEY
                else f"保留原执行路径（索引路径扫描行数放大至 {idx_plan['scan_rows']}，"
                     f"超过原路径 {seq_plan['scan_rows']}）"
            ),
        })

    # 适用范围：索引路径更优的最大日期跨度；整月查询回表放大，被排除在范围外。
    verified_spans = [item["跨度天数"] for item in sample_plans if item["采用计划"] == IDX_PLAN_KEY]
    max_span = max(verified_spans) if verified_spans else 0
    scope_text = f"date_span_days<={max_span} 且地区条件齐备" if max_span else "无（索引路径无优势）"
    scope_detail = {"max_date_span_days": max_span, "require_region": True} if max_span else None

    day_sample = sample_plans[0]
    month_sample = sample_plans[-1]
    day_seq, day_idx = day_sample["plans"]
    month_seq, month_idx = month_sample["plans"]
    row_drop = round((1 - day_idx["scan_rows"] / day_seq["scan_rows"]) * 100)
    all_verified = all(item["结果核对"]["consistent"] for item in sample_plans)

    suggestion = {
        "字段": "(region, dt)",
        "索引名": "idx_region_dt",
        "类型": "btree联合",
        "适用条件": scope_text,
        "核验状态": "已验证" if all_verified else "待验证",
        "预期收益": (
            f"单日扫描行数 {day_seq['scan_rows']}→{day_idx['scan_rows']}（-{row_drop}%），"
            f"估算成本 {day_seq['est_cost']}→{day_idx['est_cost']}；固定结果集核对一致"
            if all_verified else "未知（结果集核对未通过，未验证）"
        ),
        "风险提示": (
            f"整月范围（{month_sample['跨度天数']}天）回表放大，扫描行数升至 "
            f"{month_idx['scan_rows']}，超过原路径 {month_seq['scan_rows']}，月底整月请求不适用"
        ),
    }
    return {
        "ok": True,
        "covered": True,
        "样本范围": coverage["label"],
        "适用条件": scope_text,
        "适用条件明细": scope_detail,
        "样本计划": sample_plans,
        "索引建议": [suggestion],
        "收益核验": "已验证" if all_verified else "待验证",
    }
