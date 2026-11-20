<template>
  <section class="page" data-module="plan_decision">
    <header class="page-head">
      <div>
        <h2>执行计划视图</h2>
        <p class="page-desc">查询服务按优化分析报告的适用范围为已绑定请求选择可执行计划：列出已采纳与回退的请求，展示实际扫描节点与估算行数，采纳与回退均关联报告版本。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" data-testid="open-select" type="button" @click="openSelect">选择执行计划</button>
        <button class="btn" data-testid="open-create" type="button" @click="openCreate">登记决策</button>
        <button class="btn" data-testid="export" type="button" @click="exportRows">导出决策清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <section class="summary-panel" data-testid="class-summary">
      <h3>分类计划与成本（{{ summaryApi || '全部接口' }}）</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>请求类别</th><th>决策数</th><th>已采纳</th><th>已回退</th>
            <th>实际扫描节点</th><th>平均估算行数</th><th>平均估算成本</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in summaryClasses" :key="item.请求类别">
            <td>{{ item.请求类别 }}</td>
            <td>{{ item.决策数 }}</td>
            <td>{{ item.已采纳 }}</td>
            <td>{{ item.已回退 }}</td>
            <td>{{ item.实际扫描节点.join('；') || '—' }}</td>
            <td>{{ item.平均估算行数 ?? '—' }}</td>
            <td>{{ item.平均估算成本 ?? '—' }}</td>
          </tr>
          <tr v-if="!summaryClasses.length">
            <td colspan="7" class="empty-state">暂无决策数据</td>
          </tr>
        </tbody>
      </table>
    </section>

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
        <tr v-for="row in rows" :key="String(row.id)" :data-testid="`row-${row.id}`" :data-status="String(row.status)">
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
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无执行计划决策，可先选择执行计划</td>
        </tr>
      </tbody>
    </table>

    <div v-if="showCreate" class="modal-backdrop" data-testid="create-modal">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记决策</h3>
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

    <div v-if="showSelect" class="modal-backdrop" data-testid="select-modal">
      <form class="modal" @submit.prevent="submitSelect">
        <h3>选择执行计划</h3>
        <p class="page-desc">按本次实际绑定条件选择可执行计划；参数为空或样本不足时保留原执行路径。</p>
        <label class="create-field">
          <span>数据接口</span>
          <select v-model="selectForm.api_id" data-testid="select-api" required>
            <option v-for="api in apiOptions" :key="String(api.id)" :value="api.id">
              {{ api.接口编号 }} · {{ api.接口名称 }}
            </option>
          </select>
        </label>
        <label class="create-field">
          <span>start_date（YYYY-MM-DD，留空模拟参数为空）</span>
          <input v-model="selectForm.start_date" data-testid="select-start-date" placeholder="2026-11-15" />
        </label>
        <label class="create-field">
          <span>end_date（YYYY-MM-DD）</span>
          <input v-model="selectForm.end_date" data-testid="select-end-date" placeholder="2026-11-15" />
        </label>
        <label class="create-field">
          <span>region_list（逗号分隔）</span>
          <input v-model="selectForm.region_list" data-testid="select-region-list" placeholder="EAST,NORTH" />
        </label>
        <div class="page-actions">
          <button class="btn" type="button" @click="showSelect = false">取消</button>
          <button class="btn primary" data-testid="submit-select" type="submit" :disabled="selecting">
            {{ selecting ? '选择中…' : '选择计划' }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="lastDecision" class="modal-backdrop" data-testid="decision-result" @click.self="lastDecision = null">
      <div class="modal">
        <h3>本次计划选择结果</h3>
        <p class="decision-banner" :class="lastDecision.决策结果 === '已采纳' ? 'adopted' : 'fallback'">
          {{ lastDecision.决策结果 }} · {{ lastDecision.请求类别 }} · 报告版本 {{ lastDecision.报告版本 }}
        </p>
        <dl class="decision-grid">
          <dt>实际扫描节点</dt><dd>{{ lastDecision.扫描节点 }}</dd>
          <dt>估算行数</dt><dd>{{ lastDecision.估算行数 }}</dd>
          <dt>估算成本</dt><dd>{{ lastDecision.估算成本 }}</dd>
          <dt>结果核对</dt><dd>{{ lastDecision.结果核对 }}</dd>
          <dt v-if="lastDecision.回退原因">回退原因</dt>
          <dd v-if="lastDecision.回退原因">{{ lastDecision.回退原因 }}</dd>
        </dl>
        <table v-if="lastPlans.length" class="data-table">
          <thead>
            <tr><th>候选计划</th><th>扫描节点</th><th>估算行数</th><th>估算成本</th></tr>
          </thead>
          <tbody>
            <tr v-for="plan in lastPlans" :key="plan.plan_key">
              <td>{{ plan.plan_name }}</td>
              <td>{{ plan.scan_node }}</td>
              <td>{{ plan.scan_rows }}</td>
              <td>{{ plan.est_cost }}</td>
            </tr>
          </tbody>
        </table>
        <div class="page-actions">
          <button class="btn primary" type="button" data-testid="close-decision" @click="lastDecision = null">知道了</button>
        </div>
      </div>
    </div>

    <footer class="page-foot">
      <span>共 {{ total }} 条执行计划决策</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type Plan = { plan_key: string; plan_name: string; scan_node: string; scan_rows: number; est_cost: number }
type SummaryClass = {
  请求类别: string
  决策数: number
  已采纳: number
  已回退: number
  实际扫描节点: string[]
  平均估算行数: number | null
  平均估算成本: number | null
}

const ENDPOINT = '/api/plan_decision'
const columns = ["决策编号", "关联接口", "请求类别", "决策结果", "扫描节点", "估算行数", "报告版本", "回退原因"]
const actions = ["执行核对", "确认采纳", "归档记录"]
const statuses = ["待核对", "已核对", "已确认", "已归档"]
const metricNames = ["决策总数", "已采纳", "已回退"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const showCreate = ref(false)
const creating = ref(false)
const createValues = ref<Record<string, string>>({})
const showSelect = ref(false)
const selecting = ref(false)
const selectForm = ref<{ api_id: number | null; start_date: string; end_date: string; region_list: string }>({
  api_id: null, start_date: '', end_date: '', region_list: '',
})
const apiOptions = ref<Row[]>([])
const lastDecision = ref<Row | null>(null)
const lastPlans = ref<Plan[]>([])
const summaryClasses = ref<SummaryClass[]>([])
const summaryApi = ref('')
const stats = computed(() => [
  { label: metricNames[0], value: total.value },
  { label: metricNames[1], value: rows.value.filter((row) => row["决策结果"] === '已采纳').length },
  { label: metricNames[2], value: rows.value.filter((row) => row["决策结果"] === '已回退').length },
])

function resetFilters() {
  filters.value = {}
  void reload()
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
    link.download = 'plan_decision.csv'
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

async function openSelect() {
  errorMessage.value = ''
  try {
    const response = await request('/api/api_service?size=200')
    const payload = await response.json()
    apiOptions.value = payload.items ?? []
    if (apiOptions.value.length && selectForm.value.api_id === null) {
      selectForm.value.api_id = Number(apiOptions.value[0].id)
    }
  } catch {
    apiOptions.value = []
  }
  showSelect.value = true
}

async function submitSelect() {
  if (selectForm.value.api_id === null) return
  selecting.value = true
  errorMessage.value = ''
  try {
    const params: Record<string, unknown> = {}
    if (selectForm.value.start_date.trim()) params.start_date = selectForm.value.start_date.trim()
    if (selectForm.value.end_date.trim()) params.end_date = selectForm.value.end_date.trim()
    if (selectForm.value.region_list.trim()) {
      params.region_list = selectForm.value.region_list.split(',').map((item) => item.trim()).filter(Boolean)
    }
    const response = await request(`${ENDPOINT}/select`, {
      method: 'POST',
      body: JSON.stringify({ api_id: selectForm.value.api_id, params }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error(payload?.detail?.error || '计划选择失败')
    lastDecision.value = payload.decision
    lastPlans.value = payload.plans ?? []
    showSelect.value = false
    await Promise.all([reload(), reloadSummary()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '计划选择失败'
  } finally {
    selecting.value = false
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
      throw new Error('决策动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '决策操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('决策列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '决策列表读取失败'
  }
}

async function reloadSummary() {
  try {
    const response = await request(`${ENDPOINT}/summary`)
    const payload = await response.json()
    summaryClasses.value = payload.classes ?? []
    summaryApi.value = payload.api_code || ''
  } catch {
    summaryClasses.value = []
  }
}

onMounted(() => {
  void reload()
  void reloadSummary()
})
</script>

<style scoped>
.summary-panel { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.summary-panel h3 { margin: 0 0 8px; font-size: 14px; }
.decision-banner { padding: 8px 12px; border-radius: 6px; font-weight: 600; }
.decision-banner.adopted { background: #ecfdf3; color: #067647; }
.decision-banner.fallback { background: #fef3f2; color: #b42318; }
.decision-grid { display: grid; grid-template-columns: 120px 1fr; gap: 6px 12px; font-size: 13px; }
.decision-grid dt { color: var(--muted); }
.decision-grid dd { margin: 0; }
.create-field select { width: 100%; box-sizing: border-box; border: 1px solid var(--border); border-radius: 6px; padding: 8px; }
</style>
