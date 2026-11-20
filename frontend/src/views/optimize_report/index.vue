<template>
  <section class="page" data-module="optimize_report">
    <header class="page-head">
      <div>
        <h2>优化分析报告</h2>
        <p class="page-desc">按实际绑定条件估算的慢查询分析报告：记录不同样本数据对应的执行计划、扫描节点与索引建议，供查询服务按适用范围采用。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" data-testid="open-generate" type="button" @click="openGenerate">生成分析报告</button>
        <button class="btn" data-testid="open-create" type="button" @click="openCreate">登记报告</button>
        <button class="btn" data-testid="export" type="button" @click="exportRows">导出报告清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :data-testid="`filter-${field}`" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" data-testid="query" type="submit">查询</button>
      <button class="btn ghost" data-testid="reset" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in rows" :key="String(row.id)">
          <tr :data-testid="`row-${row.id}`" :data-status="String(row.status)">
            <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                :data-testid="`action-${row.id}-${action}`"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
              <button class="link" type="button" :data-testid="`detail-${row.id}`" @click="toggleDetail(row)">
                {{ detailId === row.id ? '收起样本' : '查看样本' }}
              </button>
            </td>
          </tr>
          <tr v-if="detailId === row.id" class="detail-row">
            <td :colspan="columns.length + 1">
              <div v-if="detailLoading" class="empty-state">样本计划加载中…</div>
              <div v-else-if="detail" class="report-detail">
                <p class="detail-line">
                  适用范围：{{ detail.适用条件 || '—' }}；收益核验：{{ detail.收益核验 }}；
                  样本范围：{{ detail.样本范围 }}
                </p>
                <table class="data-table sample-table">
                  <thead>
                    <tr>
                      <th>样本类别</th><th>绑定条件</th><th>计划</th><th>扫描节点</th>
                      <th>估算行数</th><th>估算成本</th><th>结果核对</th><th>结论</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="sample in detail.样本计划" :key="sample.样本类别">
                      <tr
                        v-for="plan in sample.plans"
                        :key="`${sample.样本类别}-${plan.plan_key}`"
                        :class="{ adopted: plan.plan_key === sample.采用计划 }"
                      >
                        <td>{{ sample.样本类别 }}</td>
                        <td>{{ formatBound(sample.绑定条件) }}</td>
                        <td>{{ plan.plan_name }}</td>
                        <td>{{ plan.scan_node }}</td>
                        <td>{{ plan.scan_rows }}</td>
                        <td>{{ plan.est_cost }}</td>
                        <td>{{ sample.结果核对?.summary ?? '—' }}</td>
                        <td>{{ plan.plan_key === sample.采用计划 ? sample.结论 : '—' }}</td>
                      </tr>
                    </template>
                    <tr v-if="!detail.样本计划?.length">
                      <td colspan="8" class="empty-state">样本不足，未生成样本计划，索引建议均为待验证</td>
                    </tr>
                  </tbody>
                </table>
                <ul class="suggestion-list">
                  <li v-for="item in detail.索引建议明细" :key="item.索引名">
                    {{ item.索引名 }}（{{ item.字段 }}，{{ item.类型 }}）· 核验状态：{{ item.核验状态 }}；
                    预期收益：{{ item.预期收益 }}；风险提示：{{ item.风险提示 }}
                  </li>
                </ul>
              </div>
            </td>
          </tr>
        </template>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无优化分析报告，可先生成分析报告</td>
        </tr>
      </tbody>
    </table>

    <div v-if="showCreate" class="modal-backdrop" data-testid="create-modal">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记报告</h3>
        <label v-for="field in columns" :key="field" class="create-field">
          <span>{{ field }}</span>
          <input v-model="createValues[field]" :data-testid="`create-${field}`" required />
        </label>
        <div class="page-actions">
          <button class="btn" type="button" @click="showCreate = false">取消</button>
          <button class="btn primary" data-testid="submit-create" type="submit" :disabled="creating">
            {{ creating ? '提交中…' : '确认登记' }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="showGenerate" class="modal-backdrop" data-testid="generate-modal">
      <form class="modal" @submit.prevent="submitGenerate">
        <h3>生成分析报告</h3>
        <p class="page-desc">按实际绑定条件对代表性样本（单日 / 一周 / 整月）估算执行计划与扫描节点，并用固定结果集核对。</p>
        <label class="create-field">
          <span>数据接口</span>
          <select v-model="generateApiId" data-testid="generate-api" required>
            <option v-for="api in apiOptions" :key="String(api.id)" :value="api.id">
              {{ api.接口编号 }} · {{ api.接口名称 }}
            </option>
          </select>
        </label>
        <div class="page-actions">
          <button class="btn" type="button" @click="showGenerate = false">取消</button>
          <button class="btn primary" data-testid="submit-generate" type="submit" :disabled="generating">
            {{ generating ? '估算中…' : '生成并发布' }}
          </button>
        </div>
      </form>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条优化分析报告</span>
      <span v-if="message" class="ok-text">{{ message }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type SamplePlan = {
  样本类别: string
  绑定条件: Record<string, string | string[]>
  plans: { plan_key: string; plan_name: string; scan_node: string; scan_rows: number; est_cost: number }[]
  结果核对?: { summary?: string }
  采用计划: string
  结论: string
}
type ReportDetail = Row & {
  样本计划?: SamplePlan[]
  索引建议明细?: { 索引名: string; 字段: string; 类型: string; 核验状态: string; 预期收益: string; 风险提示: string }[]
}

const ENDPOINT = '/api/optimize_report'
const columns = ["报告编号", "关联接口", "报告版本", "样本范围", "适用条件", "索引建议", "收益核验", "优化状态"]
const actions = ["开始分析", "发布报告", "停用报告"]
const statuses = ["草稿", "分析中", "已发布", "已停用"]
const metricNames = ["报告总数", "已发布报告", "待验证报告"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const message = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const showCreate = ref(false)
const creating = ref(false)
const createValues = ref<Record<string, string>>({})
const showGenerate = ref(false)
const generating = ref(false)
const generateApiId = ref<number | null>(null)
const apiOptions = ref<Row[]>([])
const detailId = ref<number | null>(null)
const detail = ref<ReportDetail | null>(null)
const detailLoading = ref(false)
const stats = computed(() => [
  { label: metricNames[0], value: total.value },
  { label: metricNames[1], value: rows.value.filter((row) => row.status === statuses[2]).length },
  { label: metricNames[2], value: rows.value.filter((row) => row["收益核验"] === '待验证').length },
])

function resetFilters() {
  filters.value = {}
  void reload()
}

function formatBound(bound: Record<string, string | string[]>) {
  return Object.entries(bound ?? {})
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join(',') : value}`)
    .join('，')
}

async function exportRows() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value).toString()
  try {
    const response = await request(`${ENDPOINT}/export?${query}`)
    if (!response.ok) throw new Error('导出失败，请稍后重试')
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = 'optimize_report.csv'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导出失败'
  }
}

function openCreate() {
  createValues.value = Object.fromEntries(columns.map((field) => [field, '']))
  errorMessage.value = ''
  showCreate.value = true
}

async function submitCreate() {
  creating.value = true
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST', body: JSON.stringify(createValues.value),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error(payload.message || '登记失败')
    showCreate.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  } finally {
    creating.value = false
  }
}

async function openGenerate() {
  errorMessage.value = ''
  message.value = ''
  try {
    const response = await request('/api/api_service?size=200')
    const payload = await response.json()
    apiOptions.value = payload.items ?? []
    if (apiOptions.value.length && generateApiId.value === null) {
      generateApiId.value = Number(apiOptions.value[0].id)
    }
  } catch {
    apiOptions.value = []
  }
  showGenerate.value = true
}

async function submitGenerate() {
  if (generateApiId.value === null) return
  generating.value = true
  errorMessage.value = ''
  message.value = ''
  try {
    const response = await request(`${ENDPOINT}/generate`, {
      method: 'POST', body: JSON.stringify({ api_id: generateApiId.value }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error(payload?.detail?.error || payload.message || '生成失败')
    message.value = payload.message || '报告已生成'
    showGenerate.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    generating.value = false
  }
}

async function toggleDetail(row: Row) {
  if (detailId.value === row.id) {
    detailId.value = null
    detail.value = null
    return
  }
  detailId.value = Number(row.id)
  detail.value = null
  detailLoading.value = true
  try {
    const response = await request(`${ENDPOINT}/${row.id}/detail`)
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error('报告详情读取失败')
    detail.value = payload.detail
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告详情读取失败'
    detailId.value = null
  } finally {
    detailLoading.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('报告动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('报告列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '报告列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.detail-row td { background: #f8fafc; }
.report-detail { padding: 8px; }
.detail-line { font-size: 12px; color: var(--muted); margin: 4px 0 8px; }
.sample-table th, .sample-table td { font-size: 12px; }
.sample-table tr.adopted td { background: #ecfdf3; }
.suggestion-list { margin: 8px 0 0; padding-left: 18px; font-size: 12px; color: var(--muted); }
.ok-text { color: #067647; }
.create-field select { width: 100%; box-sizing: border-box; border: 1px solid var(--border); border-radius: 6px; padding: 8px; }
</style>
