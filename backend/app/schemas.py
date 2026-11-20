"""接口出入参模型：列表分页、动作结果与各模块的明细结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class ActionResult(BaseModel):
    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    """登记或修改一条业务记录时提交的字段集合。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None


class ActionPayload(BaseModel):
    """状态动作使用独立契约，避免与登记的 values 载荷混用。"""

    action: str
    remark: str | None = None



class MetricDomainEntry(BaseModel):
    """指标域明细结构。"""

    field_0: str | None = None  # 域编号
    field_1: str | None = None  # 域名称
    field_2: str | None = None  # 业务域描述
    field_3: str | None = None  # 数据源表
    field_4: str | None = None  # 更新频率
    field_5: str | None = None  # 负责人
    field_6: str | None = None  # 域状态
    field_7: str | None = None  # 创建时间

class DerivedMetricEntry(BaseModel):
    """派生指标明细结构。"""

    field_0: str | None = None  # 指标编号
    field_1: str | None = None  # 父指标编号
    field_2: str | None = None  # 计算公式
    field_3: str | None = None  # 统计周期
    field_4: str | None = None  # 业务限定
    field_5: str | None = None  # 统计粒度
    field_6: str | None = None  # 精度位数
    field_7: str | None = None  # 口径版本

class ApiServiceEntry(BaseModel):
    """数据接口明细结构。"""

    field_0: str | None = None  # 接口编号
    field_1: str | None = None  # 接口名称
    field_2: str | None = None  # 查询SQL
    field_3: str | None = None  # 参数列表
    field_4: str | None = None  # 返回字段
    field_5: str | None = None  # 缓存时长
    field_6: str | None = None  # 限流阈值
    field_7: str | None = None  # 接口版本

class QueryOptimizeEntry(BaseModel):
    """优化建议明细结构。"""

    field_0: str | None = None  # 建议编号
    field_1: str | None = None  # 关联接口
    field_2: str | None = None  # 慢查询摘要
    field_3: str | None = None  # 执行计划
    field_4: str | None = None  # 索引建议
    field_5: str | None = None  # 分区裁剪
    field_6: str | None = None  # 预期提升
    field_7: str | None = None  # 优化状态

class OptimizeReportEntry(BaseModel):
    """优化分析报告明细结构。"""

    field_0: str | None = None  # 报告编号
    field_1: str | None = None  # 关联接口
    field_2: str | None = None  # 报告版本
    field_3: str | None = None  # 样本范围
    field_4: str | None = None  # 适用条件
    field_5: str | None = None  # 索引建议
    field_6: str | None = None  # 收益核验
    field_7: str | None = None  # 优化状态

class PlanDecisionEntry(BaseModel):
    """执行计划决策明细结构。"""

    field_0: str | None = None  # 决策编号
    field_1: str | None = None  # 关联接口
    field_2: str | None = None  # 请求类别
    field_3: str | None = None  # 决策结果
    field_4: str | None = None  # 扫描节点
    field_5: str | None = None  # 估算行数
    field_6: str | None = None  # 报告版本
    field_7: str | None = None  # 回退原因

class ApiSubscribeEntry(BaseModel):
    """订阅记录明细结构。"""

    field_0: str | None = None  # 订阅编号
    field_1: str | None = None  # 接口编号
    field_2: str | None = None  # 订阅方
    field_3: str | None = None  # 调用配额
    field_4: str | None = None  # 有效期至
    field_5: str | None = None  # WebHook回调
    field_6: str | None = None  # 订阅状态
    field_7: str | None = None  # QPS上限

class CallCredentialEntry(BaseModel):
    """访问凭证明细结构。"""

    field_0: str | None = None  # 凭证编号
    field_1: str | None = None  # 订阅方
    field_2: str | None = None  # 凭证摘要
    field_3: str | None = None  # 签发时间
    field_4: str | None = None  # 过期时间
    field_5: str | None = None  # 调用范围
    field_6: str | None = None  # 最后使用
    field_7: str | None = None  # 凭证状态

class DatasourceConnectEntry(BaseModel):
    """连接配置明细结构。"""

    field_0: str | None = None  # 连接编号
    field_1: str | None = None  # 数据源类型
    field_2: str | None = None  # 连接地址
    field_3: str | None = None  # 认证方式
    field_4: str | None = None  # 数据库名
    field_5: str | None = None  # 连接池大小
    field_6: str | None = None  # 连接超时
    field_7: str | None = None  # 最后校验

class CallTraceEntry(BaseModel):
    """调用记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 接口编号
    field_2: str | None = None  # 调用方
    field_3: str | None = None  # 请求参数
    field_4: str | None = None  # 返回行数
    field_5: str | None = None  # 耗时毫秒
    field_6: str | None = None  # 状态码
    field_7: str | None = None  # 调用时间

class DataPreviewEntry(BaseModel):
    """预览模板明细结构。"""

    field_0: str | None = None  # 模板编号
    field_1: str | None = None  # 数据源名
    field_2: str | None = None  # 预查询SQL
    field_3: str | None = None  # 返回列数
    field_4: str | None = None  # 采样行数
    field_5: str | None = None  # 缓存秒数
    field_6: str | None = None  # 刷新策略
    field_7: str | None = None  # 模板版本

class ApiVersionEntry(BaseModel):
    """版本管理明细结构。"""

    field_0: str | None = None  # 版本编号
    field_1: str | None = None  # 接口编号
    field_2: str | None = None  # 变更说明
    field_3: str | None = None  # 旧SQL摘要
    field_4: str | None = None  # 新SQL摘要
    field_5: str | None = None  # 兼容标记
    field_6: str | None = None  # 生效时间
    field_7: str | None = None  # 回滚版本

class BatchExportEntry(BaseModel):
    """导出任务明细结构。"""

    field_0: str | None = None  # 任务编号
    field_1: str | None = None  # 查询SQL
    field_2: str | None = None  # 导出格式
    field_3: str | None = None  # 字段映射
    field_4: str | None = None  # 分片策略
    field_5: str | None = None  # 压缩编码
    field_6: str | None = None  # 写入路径
    field_7: str | None = None  # 结果校验

class MetricHomonymEntry(BaseModel):
    """重名记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 指标名称
    field_2: str | None = None  # 口径A来源
    field_3: str | None = None  # 口径B来源
    field_4: str | None = None  # 差异说明
    field_5: str | None = None  # 裁决结果
    field_6: str | None = None  # 生效域
    field_7: str | None = None  # 裁决时间

class DataAggregateEntry(BaseModel):
    """聚合配置明细结构。"""

    field_0: str | None = None  # 配置编号
    field_1: str | None = None  # 数据来源
    field_2: str | None = None  # 聚合维度
    field_3: str | None = None  # 聚合函数
    field_4: str | None = None  # 过滤条件
    field_5: str | None = None  # 输出表名
    field_6: str | None = None  # 增量键
    field_7: str | None = None  # 更新策略

class DataCleanseEntry(BaseModel):
    """清洗配置明细结构。"""

    field_0: str | None = None  # 配置编号
    field_1: str | None = None  # 数据来源
    field_2: str | None = None  # 清洗字段
    field_3: str | None = None  # 清洗规则
    field_4: str | None = None  # 默认替换值
    field_5: str | None = None  # 空值策略
    field_6: str | None = None  # 异常阈值
    field_7: str | None = None  # 结果表名

class AccessDashboardEntry(BaseModel):
    """访问统计明细结构。"""

    field_0: str | None = None  # 统计编号
    field_1: str | None = None  # 接口编号
    field_2: str | None = None  # 调用方
    field_3: str | None = None  # 今日调用量
    field_4: str | None = None  # 平均耗时
    field_5: str | None = None  # 失败率
    field_6: str | None = None  # 数据量
    field_7: str | None = None  # 最近调用

class SqlTemplateEntry(BaseModel):
    """模板定义明细结构。"""

    field_0: str | None = None  # 模板编号
    field_1: str | None = None  # 模板名称
    field_2: str | None = None  # SQL片段
    field_3: str | None = None  # 参数标记
    field_4: str | None = None  # 参数类型
    field_5: str | None = None  # 默认值
    field_6: str | None = None  # 使用次数
    field_7: str | None = None  # 模板版本

class ResultCacheEntry(BaseModel):
    """缓存配置明细结构。"""

    field_0: str | None = None  # 配置编号
    field_1: str | None = None  # 缓存键
    field_2: str | None = None  # 缓存引擎
    field_3: str | None = None  # 过期策略
    field_4: str | None = None  # 最大容量
    field_5: str | None = None  # 淘汰算法
    field_6: str | None = None  # 命中率阈值
    field_7: str | None = None  # 配置版本

class QueryAuditEntry(BaseModel):
    """审计日志明细结构。"""

    field_0: str | None = None  # 日志编号
    field_1: str | None = None  # 接口编号
    field_2: str | None = None  # 调用方
    field_3: str | None = None  # 请求参数
    field_4: str | None = None  # 返回行数
    field_5: str | None = None  # 数据敏感度
    field_6: str | None = None  # 审计结论
    field_7: str | None = None  # 审计时间
