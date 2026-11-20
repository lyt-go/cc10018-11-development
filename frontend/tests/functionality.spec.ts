import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

type ModuleCase = {
  key: string
  fields: string[]
  actions: string[]
  actionTargets: string[]
  shape: string
}

const modules: ModuleCase[] = [
  {
    "key": "metric_domain",
    "fields": [
      "域编号",
      "域名称",
      "业务域描述",
      "数据源表",
      "更新频率",
      "负责人",
      "域状态",
      "创建时间"
    ],
    "actions": [
      "提交校验",
      "开启域",
      "停用域"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "derived_metric",
    "fields": [
      "指标编号",
      "父指标编号",
      "计算公式",
      "统计周期",
      "业务限定",
      "统计粒度",
      "精度位数",
      "口径版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "标记废弃"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已废弃"
    ],
    "shape": "crud-table"
  },
  {
    "key": "api_service",
    "fields": [
      "接口编号",
      "接口名称",
      "查询SQL",
      "参数列表",
      "返回字段",
      "缓存时长",
      "限流阈值",
      "接口版本"
    ],
    "actions": [
      "提交校验",
      "发布接口",
      "下线接口"
    ],
    "actionTargets": [
      "待校验",
      "已发布",
      "已下线"
    ],
    "shape": "crud-table"
  },
  {
    "key": "query_optimize",
    "fields": [
      "建议编号",
      "关联接口",
      "慢查询摘要",
      "执行计划",
      "索引建议",
      "分区裁剪",
      "预期提升",
      "优化状态"
    ],
    "actions": [
      "开始分析",
      "开始优化",
      "确认完成"
    ],
    "actionTargets": [
      "分析中",
      "优化中",
      "已完成"
    ],
    "shape": "crud-table"
  },
  {
    "key": "optimize_report",
    "fields": [
      "报告编号",
      "关联接口",
      "报告版本",
      "样本范围",
      "适用条件",
      "索引建议",
      "收益核验",
      "优化状态"
    ],
    "actions": [
      "开始分析",
      "发布报告",
      "停用报告"
    ],
    "actionTargets": [
      "分析中",
      "已发布",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "plan_decision",
    "fields": [
      "决策编号",
      "关联接口",
      "请求类别",
      "决策结果",
      "扫描节点",
      "估算行数",
      "报告版本",
      "回退原因"
    ],
    "actions": [
      "执行核对",
      "确认采纳",
      "归档记录"
    ],
    "actionTargets": [
      "已核对",
      "已确认",
      "已归档"
    ],
    "shape": "crud-table"
  },
  {
    "key": "api_subscribe",
    "fields": [
      "订阅编号",
      "接口编号",
      "订阅方",
      "调用配额",
      "有效期至",
      "WebHook回调",
      "订阅状态",
      "QPS上限"
    ],
    "actions": [
      "提交审批",
      "开通订阅",
      "终止订阅"
    ],
    "actionTargets": [
      "待审批",
      "已生效",
      "已终止"
    ],
    "shape": "crud-table"
  },
  {
    "key": "call_credential",
    "fields": [
      "凭证编号",
      "订阅方",
      "凭证摘要",
      "签发时间",
      "过期时间",
      "调用范围",
      "最后使用",
      "凭证状态"
    ],
    "actions": [
      "激活凭证",
      "标记过期",
      "吊销凭证"
    ],
    "actionTargets": [
      "使用中",
      "已过期",
      "已吊销"
    ],
    "shape": "crud-table"
  },
  {
    "key": "datasource_connect",
    "fields": [
      "连接编号",
      "数据源类型",
      "连接地址",
      "认证方式",
      "数据库名",
      "连接池大小",
      "连接超时",
      "最后校验"
    ],
    "actions": [
      "提交校验",
      "标记连接",
      "标记断开"
    ],
    "actionTargets": [
      "待校验",
      "已连接",
      "已断开"
    ],
    "shape": "crud-table"
  },
  {
    "key": "call_trace",
    "fields": [
      "记录编号",
      "接口编号",
      "调用方",
      "请求参数",
      "返回行数",
      "耗时毫秒",
      "状态码",
      "调用时间"
    ],
    "actions": [
      "标记慢查询",
      "标记异常",
      "归档记录"
    ],
    "actionTargets": [
      "慢查询",
      "异常",
      "已归档"
    ],
    "shape": "crud-table"
  },
  {
    "key": "data_preview",
    "fields": [
      "模板编号",
      "数据源名",
      "预查询SQL",
      "返回列数",
      "采样行数",
      "缓存秒数",
      "刷新策略",
      "模板版本"
    ],
    "actions": [
      "提交校验",
      "启用模板",
      "停用模板"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "api_version",
    "fields": [
      "版本编号",
      "接口编号",
      "变更说明",
      "旧SQL摘要",
      "新SQL摘要",
      "兼容标记",
      "生效时间",
      "回滚版本"
    ],
    "actions": [
      "开始灰度",
      "全量发布",
      "执行回滚"
    ],
    "actionTargets": [
      "灰度中",
      "已全量",
      "已回滚"
    ],
    "shape": "crud-table"
  },
  {
    "key": "batch_export",
    "fields": [
      "任务编号",
      "查询SQL",
      "导出格式",
      "字段映射",
      "分片策略",
      "压缩编码",
      "写入路径",
      "结果校验"
    ],
    "actions": [
      "启动导出",
      "确认完成",
      "标记失败"
    ],
    "actionTargets": [
      "运行中",
      "已完成",
      "已失败"
    ],
    "shape": "job-timeline"
  },
  {
    "key": "metric_homonym",
    "fields": [
      "记录编号",
      "指标名称",
      "口径A来源",
      "口径B来源",
      "差异说明",
      "裁决结果",
      "生效域",
      "裁决时间"
    ],
    "actions": [
      "发起裁决",
      "确认统一",
      "保留双口径"
    ],
    "actionTargets": [
      "待裁决",
      "已统一",
      "已保留双口径"
    ],
    "shape": "crud-table"
  },
  {
    "key": "data_aggregate",
    "fields": [
      "配置编号",
      "数据来源",
      "聚合维度",
      "聚合函数",
      "过滤条件",
      "输出表名",
      "增量键",
      "更新策略"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "data_cleanse",
    "fields": [
      "配置编号",
      "数据来源",
      "清洗字段",
      "清洗规则",
      "默认替换值",
      "空值策略",
      "异常阈值",
      "结果表名"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "access_dashboard",
    "fields": [
      "统计编号",
      "接口编号",
      "调用方",
      "今日调用量",
      "平均耗时",
      "失败率",
      "数据量",
      "最近调用"
    ],
    "actions": [
      "提交校验",
      "开启监控",
      "停用监控"
    ],
    "actionTargets": [
      "待校验",
      "监控中",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "sql_template",
    "fields": [
      "模板编号",
      "模板名称",
      "SQL片段",
      "参数标记",
      "参数类型",
      "默认值",
      "使用次数",
      "模板版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "标记废弃"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已废弃"
    ],
    "shape": "crud-table"
  },
  {
    "key": "result_cache",
    "fields": [
      "配置编号",
      "缓存键",
      "缓存引擎",
      "过期策略",
      "最大容量",
      "淘汰算法",
      "命中率阈值",
      "配置版本"
    ],
    "actions": [
      "提交校验",
      "标记生效",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已生效",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "query_audit",
    "fields": [
      "日志编号",
      "接口编号",
      "调用方",
      "请求参数",
      "返回行数",
      "数据敏感度",
      "审计结论",
      "审计时间"
    ],
    "actions": [
      "标记待审核",
      "标记违规",
      "归档记录"
    ],
    "actionTargets": [
      "待审核",
      "已违规",
      "已归档"
    ],
    "shape": "crud-table"
  }
]
const repoKind = 'fullstack'
const crudModules = modules.filter(m => m.shape === 'crud-table')
const dagModules = modules.filter(m => m.shape === 'dag-graph')
const timelineModules = modules.filter(m => m.shape === 'job-timeline')
const analysisModules = modules.filter(m => m.shape === 'analysis-dashboard')

function parseCsv(text: string): string[][] {
  const records: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  const input = text.replace(/^\uFEFF/, '')
  for (let index = 0; index < input.length; index++) {
    const char = input[index]
    if (quoted) {
      if (char === '"' && input[index + 1] === '"') { cell += '"'; index++ }
      else if (char === '"') { quoted = false }
      else { cell += char }
    } else if (char === '"' && cell === '') { quoted = true }
    else if (char === ',') { row.push(cell); cell = '' }
    else if (char === '\n') {
      row.push(cell.replace(/\r$/, ''))
      if (row.some(v => v !== '')) records.push(row)
      row = []; cell = ''
    } else { cell += char }
  }
  row.push(cell.replace(/\r$/, ''))
  if (row.some(v => v !== '')) records.push(row)
  return records
}

test('CRUD模块：筛选、导出、登记、动作、指标全链路', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (crudModules.length === 0) { test.skip(); return }

  for (const mod of crudModules) {
    await page.goto(`/${mod.key}`)
    await page.waitForTimeout(3000)
    const bodyRows = page.locator('tbody tr[data-testid^="row-"]')
    await expect(bodyRows).toHaveCount(3)
    const firstValue = await bodyRows.nth(0).locator('td').nth(0).innerText()

    await page.getByTestId(`filter-${mod.fields[0]}`).fill(firstValue)
    await page.getByTestId('query').click()
    await expect(bodyRows).toHaveCount(1)
    await page.getByTestId('reset').click()
    await expect(bodyRows).toHaveCount(3)

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    const createdValues = mod.fields.map((f, i) => `验收-${mod.key}-${i+1}`)
    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.entries()) {
      await page.getByTestId(`create-${field}`).fill(createdValues[i])
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
    await expect(bodyRows).toHaveCount(4)

    const createdRow = page.locator('tbody tr').filter({ hasText: createdValues[0] })
    for (const [i, action] of mod.actions.entries()) {
      await createdRow.getByRole('button', { name: action, exact: true }).click()
      await expect(createdRow).toHaveAttribute('data-status', mod.actionTargets[i])
    }
  }

  expect(browserErrors).toEqual([])
})

test('DAG拓扑模块：节点渲染、详情、动作、导出', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (dagModules.length === 0) { test.skip(); return }

  for (const mod of dagModules) {
    await page.goto(`/${mod.key}`)
    await page.waitForTimeout(3000)
    await expect(page.locator('svg.dag-svg')).toBeVisible()
    const nodes = page.locator('g.dag-node')
    const count = await nodes.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await nodes.first().click()
    await expect(page.getByTestId('dag-detail')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('时间线模块：甘特条渲染、日期筛选、日志查看、登记', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (timelineModules.length === 0) { test.skip(); return }

  for (const mod of timelineModules) {
    await page.goto(`/${mod.key}`)
    await expect(page.locator('.timeline-bar').first()).toBeVisible({ timeout: 10000 })
    const bars = page.locator('.timeline-bar')
    const count = await bars.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await bars.first().click()
    await expect(page.getByTestId('timeline-log')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('分析看板模块：KPI卡片、运行分析、图表渲染', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (analysisModules.length === 0) { test.skip(); return }

  for (const mod of analysisModules) {
    await page.goto(`/${mod.key}`)
    await expect(page.getByTestId('kpi-card').first()).toBeVisible({ timeout: 10000 })
    const kpiCards = page.getByTestId('kpi-card')
    const kpiCount = await kpiCards.count()
    expect(kpiCount).toBeGreaterThanOrEqual(2)
    await expect(kpiCards.first().locator('strong')).toBeVisible()

    await page.getByTestId('run-analysis').click()
    await expect(page.locator('.analysis-bar').first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.data-table tbody tr').first()).toBeVisible({ timeout: 5000 })
  }

  expect(browserErrors).toEqual([])
})

test('概览汇总', async ({ page }) => {
  test.setTimeout(300_000)
  await page.goto('/')
  await expect(page.locator('.stat-value').nth(1)).toBeVisible()
  // 验证概览页加载正常即可，不硬编码精确计数（取决于各模块 E2E 登记成功数）
})
