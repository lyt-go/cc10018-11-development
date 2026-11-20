# 指标服务与数据开放平台

面向指标口径管理、数据服务编排、API发布与调用治理的数据开放与分析平台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 指标域管理 | `metric_domain` | 指标域 | 域编号、域名称、业务域描述 |
| 派生指标 | `derived_metric` | 派生指标 | 指标编号、父指标编号、计算公式 |
| API服务 | `api_service` | 数据接口 | 接口编号、接口名称、查询SQL |
| 查询优化 | `query_optimize` | 优化建议 | 建议编号、关联接口、慢查询摘要 |
| 优化分析报告 | `optimize_report` | 分析报告 | 报告编号、报告版本、适用条件 |
| 执行计划视图 | `plan_decision` | 计划决策 | 决策编号、决策结果、扫描节点 |
| 接口订阅 | `api_subscribe` | 订阅记录 | 订阅编号、接口编号、订阅方 |
| 调用凭证 | `call_credential` | 访问凭证 | 凭证编号、订阅方、凭证摘要 |
| 数据源连接 | `datasource_connect` | 连接配置 | 连接编号、数据源类型、连接地址 |
| 调用追踪 | `call_trace` | 调用记录 | 记录编号、接口编号、调用方 |
| 数据预览 | `data_preview` | 预览模板 | 模板编号、数据源名、预查询SQL |
| 接口版本 | `api_version` | 版本管理 | 版本编号、接口编号、变更说明 |
| 批量导出 | `batch_export` | 导出任务 | 任务编号、查询SQL、导出格式 |
| 指标重名解析 | `metric_homonym` | 重名记录 | 记录编号、指标名称、口径A来源 |
| 数据聚合 | `data_aggregate` | 聚合配置 | 配置编号、数据来源、聚合维度 |
| 数据清洗 | `data_cleanse` | 清洗配置 | 配置编号、数据来源、清洗字段 |
| 访问看板 | `access_dashboard` | 访问统计 | 统计编号、接口编号、调用方 |
| SQL模板 | `sql_template` | 模板定义 | 模板编号、模板名称、SQL片段 |
| 结果缓存 | `result_cache` | 缓存配置 | 配置编号、缓存键、缓存引擎 |
| 查询审计 | `query_audit` | 审计日志 | 日志编号、接口编号、调用方 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数据分析与数据应用
