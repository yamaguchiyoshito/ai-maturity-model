<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, computed, ref } from 'vue'
import { withBase } from 'vitepress'

/**
 * 成熟度マトリクスの自己評価。軸ごとに1レベル、自動化段階を1つ選び、判定規則（PJのレベルは5軸の最小値、
 * 自動化段階は前提レベルを超えると統制不足）を当てた結果をページ内で集計する。記録はこのブラウザの localStorage にだけ保存する。
 * 表の文面とモデルの数値は docs/model/matrix.md（criteria/model.json から生成）の data 属性から読む。
 */
const KEY = 'ai-maturity.matrix.v1'
type Model = {
  levels: Record<string, string>
  next: Record<string, string | null>
  maxStage: Record<string, string>
  orgLevels: number[]
  axes: { id: string; name: string }[]
  estimateAxis: string
  stages: Record<string, { name: string; posture: string; minLevel: number }>
  effects: Record<string, { task: string; project: string; handling: string }>
  effectRules: { coefficient: string; commit_level: number; commit: string }
}
type AxisRow = { id: string; name: string; cells: HTMLTableCellElement[] }
const model = ref<Model | null>(null)
const axisRows: AxisRow[] = []
let stageCells: HTMLTableCellElement[] = []
let stageColumns: HTMLElement[] = []
let levelColumns: HTMLElement[] = []
const state = reactive<{ target: string; updated: string | null; levels: Record<string, number>; stage: string | null; ready: boolean }>({ target: '', updated: null, levels: {}, stage: null, ready: false })
const copied = ref(false)
const cleanups: (() => void)[] = []

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (!data || typeof data !== 'object') return
    state.target = typeof data.target === 'string' ? data.target.slice(0, 80) : ''
    state.updated = typeof data.updated === 'string' ? data.updated : null
    if (data.levels && typeof data.levels === 'object') {
      for (const [k, lv] of Object.entries(data.levels)) if (Number.isInteger(lv) && (lv as number) >= 0 && (lv as number) <= 5) state.levels[k] = lv as number
    }
    if (typeof data.stage === 'string' && ['0', 'A1', 'A2', 'A3', 'A4'].includes(data.stage)) state.stage = data.stage
  } catch { /* プライベートモード等で localStorage が使えなくても、保存なしで動作する */ }
}
function save() {
  state.updated = new Date().toISOString()
  try { localStorage.setItem(KEY, JSON.stringify({ version: 1, target: state.target, updated: state.updated, levels: state.levels, stage: state.stage })) } catch { /* ignore */ }
}
function paintAxis(row: AxisRow) {
  const lv = state.levels[row.id]
  row.cells.forEach((td) => {
    const n = Number(td.dataset.level)
    td.setAttribute('aria-pressed', lv === n ? 'true' : 'false')
    td.classList.toggle('is-selected', lv === n)
    td.classList.toggle('is-passed', lv !== undefined && n < lv)
  })
}
function paintStage() {
  stageCells.forEach((td) => {
    const on = state.stage !== null && td.dataset.stage === state.stage
    td.setAttribute('aria-pressed', on ? 'true' : 'false')
    td.classList.toggle('is-selected', on)
  })
  stageColumns.forEach((el) => el.classList.toggle('is-current', state.stage !== null && el.dataset.stage === state.stage))
}
function paintLevel() {
  const lv = pjLevel.value
  levelColumns.forEach((el) => el.classList.toggle('is-current', lv !== null && lv > 0 && Number(el.dataset.level) === lv))
}
function selectAxis(row: AxisRow, lv: number) {
  if (state.levels[row.id] === lv) delete state.levels[row.id]; else state.levels[row.id] = lv // 同じセルの再クリックで解除
  save(); paintAxis(row); paintLevel()
}
function selectStage(key: string) {
  state.stage = state.stage === key ? null : key
  save(); paintStage()
}
function clearAll() {
  if (!confirm('この端末に保存した自己評価と評価対象名をすべて消去します。よろしいですか？')) return
  for (const k of Object.keys(state.levels)) delete state.levels[k]
  state.stage = null; state.target = ''; state.updated = null
  try { localStorage.removeItem(KEY) } catch { /* ignore */ }
  axisRows.forEach(paintAxis); paintStage(); paintLevel()
}
function onTargetChange(e: Event) { state.target = (e.target as HTMLInputElement).value.trim().slice(0, 80); save() }
function bind(td: HTMLTableCellElement, fn: () => void) {
  const onClick = (e: Event) => { if ((e.target as HTMLElement).closest('a, summary, details')) return; fn() }
  const onKey = (e: KeyboardEvent) => { if (e.target === td && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); fn() } }
  td.addEventListener('click', onClick); td.addEventListener('keydown', onKey)
  cleanups.push(() => { td.removeEventListener('click', onClick); td.removeEventListener('keydown', onKey) })
}

onMounted(() => {
  const holder = document.querySelector<HTMLElement>('.mm-data')
  try { model.value = JSON.parse(holder?.dataset.model || 'null') } catch { model.value = null }
  if (!model.value) return
  load()
  for (const tr of Array.from(document.querySelectorAll<HTMLTableRowElement>('.mm-matrix-axes tbody tr[data-axis]'))) {
    const row: AxisRow = { id: tr.dataset.axis!, name: tr.dataset.axisName || tr.dataset.axis!, cells: Array.from(tr.querySelectorAll<HTMLTableCellElement>('td.mm-cell')) }
    row.cells.forEach((td) => bind(td, () => selectAxis(row, Number(td.dataset.level))))
    axisRows.push(row); paintAxis(row)
  }
  stageCells = Array.from(document.querySelectorAll<HTMLTableCellElement>('.mm-matrix-stages td.mm-stage-cell'))
  stageCells.forEach((td) => bind(td, () => selectStage(td.dataset.stage!)))
  stageColumns = Array.from(document.querySelectorAll<HTMLElement>('.mm-matrix-stages [data-stage]'))
  levelColumns = Array.from(document.querySelectorAll<HTMLElement>('.mm-matrix-levels [data-level]'))
  paintStage(); paintLevel()
  state.ready = true
})
onBeforeUnmount(() => cleanups.forEach((f) => f()))

const m = computed(() => model.value!)
const rows = computed(() => m.value.axes.map((a) => ({ ...a, level: state.levels[a.id] ?? null })))
const selected = computed(() => rows.value.filter((r) => r.level !== null))
const pending = computed(() => rows.value.filter((r) => r.level === null))
/** PJのレベル＝選択済み軸の最小値。全軸未選択なら null。未選択の軸が残っていれば暫定。 */
const pjLevel = computed(() => (selected.value.length ? Math.min(...selected.value.map((r) => r.level as number)) : null))
const constraining = computed(() => (pjLevel.value === null ? [] : selected.value.filter((r) => r.level === pjLevel.value)))
const provisional = computed(() => pending.value.length > 0)
const levelLabel = (lv: number | null) => (lv === null ? '未選択' : lv === 0 ? '未到達' : `レベル${lv} ${m.value.levels[String(lv)]}`)
const stageLabel = (key: string | null) => (key === null ? '未選択' : key === '0' ? '自動化段階なし' : `${key} ${m.value.stages[key].posture}`)
/** 統制不足：選択した段階の前提レベルが、PJのレベルを超えている。 */
const control = computed(() => {
  if (state.stage === null || pjLevel.value === null) return null
  const need = m.value.stages[state.stage].minLevel
  return { need, excess: need > pjLevel.value, limit: m.value.maxStage[String(pjLevel.value)] }
})
const nextCondition = computed(() => (pjLevel.value === null ? null : m.value.next[String(pjLevel.value)]))
const orgNote = computed(() => selected.value.filter((r) => m.value.orgLevels.includes(r.level as number)))
/** 見積もりで使える削減率：見積もり・PJ収支を除く4軸の最小レベルに対応する目安値が上限。 */
const effect = computed(() => {
  const four = selected.value.filter((r) => r.id !== m.value.estimateAxis)
  if (four.length === 0) return null
  const lv = Math.min(...four.map((r) => r.level as number))
  const e = m.value.effects[String(lv)]
  const est = state.levels[m.value.estimateAxis]
  return { lv, e, partial: four.length < m.value.axes.length - 1, commit: est !== undefined && est >= m.value.effectRules.commit_level }
})
const updatedLabel = computed(() => {
  if (!state.updated) return '—'
  const d = new Date(state.updated); if (isNaN(d.getTime())) return '—'
  const p = (n: number) => (n < 10 ? '0' : '') + n
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
})
const markdown = computed(() => {
  const lines = [`# AI利用成熟度 自己評価${state.target ? '：' + state.target : ''}`, '', `- 評価日：${(state.updated ?? new Date().toISOString()).slice(0, 10)}`, '- 種別：申告に基づく自己評価（証拠未確認。確定には評価の進め方の手順で証拠を確認する）', '']
  lines.push('| 評価軸 | 自己評価 | 次のレベルへ |', '|---|---|---|')
  for (const r of rows.value) {
    const nxt = r.level === null ? '—' : r.level >= 5 ? '最高レベル' : `レベル${r.level + 1} ${m.value.levels[String(r.level + 1)]}`
    lines.push(`| ${r.name} | ${levelLabel(r.level)} | ${nxt} |`)
  }
  lines.push('')
  lines.push(`- **PJのレベル**：${levelLabel(pjLevel.value)}${provisional.value && pjLevel.value !== null ? '（暫定。未選択の軸があります）' : ''}`)
  if (constraining.value.length) lines.push(`- **制約になっている軸**：${constraining.value.map((r) => r.name).join('、')}`)
  lines.push(`- **自動化段階**：${stageLabel(state.stage)}`)
  if (control.value) lines.push(control.value.excess ? `- **統制状態**：統制不足。${state.stage} はレベル${control.value.need}以上を前提とするが、PJのレベルは${levelLabel(pjLevel.value)}` : `- **統制状態**：統制範囲内（自動化段階の上限 ${control.value.limit}）`)
  if (effect.value) lines.push(`- **見積もりに使える削減率の上限（目安）**：AI適用作業 ${effect.value.e.task}、案件全体 ${effect.value.e.project}（${effect.value.e.handling}）`)
  return lines.join('\n') + '\n'
})
async function copy() {
  try { await navigator.clipboard.writeText(markdown.value); copied.value = true; setTimeout(() => (copied.value = false), 2000) } catch { copied.value = false }
}
const link = (p: string) => withBase(p)
</script>

<template>
  <section v-if="model" class="mm-summary" aria-labelledby="mm-summary-title">
    <h2 id="mm-summary-title" class="mm-summary-title">自己評価の記録と集計<span>この端末のブラウザにだけ保存されます</span></h2>
    <p class="mm-help">下の「軸別レベル」の表で各軸の現状に最も近いセルを、「自動化段階」の表で実行記録で確認できた段階を選んでください。同じセルをもう一度選ぶと解除されます。</p>
    <div v-if="state.ready" class="mm-body">
      <div class="mm-meta">
        <label>評価対象 <input id="mm-target" type="text" :value="state.target" placeholder="PJ名" maxlength="80" @change="onTargetChange"></label>
        <span class="mm-updated">最終更新：{{ updatedLabel }}</span>
      </div>
      <div class="mm-stats" role="group" aria-label="集計">
        <span class="stat stat-primary"><strong>{{ selected.length }}<small>/{{ rows.length }}</small></strong>軸を選択済み</span>
        <span class="stat"><strong>{{ pending.length }}</strong>未選択</span>
        <span class="stat"><strong>{{ state.stage === null ? '—' : state.stage === '0' ? 'なし' : state.stage }}</strong>自動化段階</span>
      </div>
      <table class="mm-axes-summary">
        <thead><tr><th>評価軸</th><th>自己評価</th><th>次のレベルへ</th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.name }}</td>
            <td><span class="mm-pill" :class="{ 'mm-pill-none': r.level === null }">{{ levelLabel(r.level) }}</span></td>
            <td>
              <template v-if="r.level === null">—</template>
              <template v-else-if="r.level >= 5">最高レベル</template>
              <a v-else :href="link('/assess/howto.html#次のレベルへの施策')">{{ r.level === 0 ? '未到達' : r.level }} → {{ r.level + 1 }} の施策</a>
            </td>
          </tr>
        </tbody>
      </table>
      <dl class="mm-result" data-testid="mm-result">
        <div>
          <dt>PJのレベル</dt>
          <dd>
            <strong data-testid="mm-pj-level">{{ levelLabel(pjLevel) }}</strong>
            <span v-if="pjLevel !== null && provisional" class="mm-note">暫定。未選択の軸が {{ pending.length }} つあります</span>
            <span v-if="constraining.length" class="mm-note" data-testid="mm-constraint">制約になっている軸：{{ constraining.map(r => r.name).join('、') }}</span>
            <span v-if="pjLevel !== null && nextCondition" class="mm-note">次のレベルへ上がる条件：{{ nextCondition }}</span>
            <span v-if="orgNote.length" class="mm-note">{{ orgNote.map(r => r.name).join('、') }}はレベル4以上を選んでいます。レベル4・5はPJ単独では判定せず、組織側の整備が到達条件です</span>
          </dd>
        </div>
        <div>
          <dt>自動化段階</dt>
          <dd>
            <strong data-testid="mm-stage">{{ stageLabel(state.stage) }}</strong>
            <span v-if="control && control.excess" class="mm-alert" data-testid="mm-control-excess">統制不足：{{ state.stage }} はレベル{{ control.need }}以上を前提としますが、PJのレベルは{{ levelLabel(pjLevel) }}です。自動化を先に進めず、制約になっている軸を引き上げてください</span>
            <span v-else-if="control" class="mm-ok" data-testid="mm-control-ok">統制範囲内。PJのレベルでの自動化段階の上限は {{ control.limit }} です</span>
            <span v-else class="mm-note">軸と段階の両方を選ぶと、統制不足の有無を判定します</span>
          </dd>
        </div>
        <div>
          <dt>見積もりの目安</dt>
          <dd>
            <template v-if="effect">
              <strong data-testid="mm-effect">AI適用作業 {{ effect.e.task }}／案件全体 {{ effect.e.project }}</strong>
              <span class="mm-note">{{ effect.e.handling }}。見積もり・PJ収支を除く4軸の最小レベル{{ effect.partial ? '（選択済みの軸のみ）' : '' }}に対応する目安値で、これが上限です</span>
              <span class="mm-note">{{ effect.commit ? '見積もり・PJ収支がレベル4以上のため、削減効果を価格や納期として確約できます' : '削減効果を価格や納期として確約できるのは、見積もり・PJ収支がレベル4以上の場合です' }}</span>
            </template>
            <span v-else class="mm-note">見積もり・PJ収支以外の軸を選ぶと表示します</span>
          </dd>
        </div>
      </dl>
      <p class="mm-caution">この結果は申告に基づく自己評価です。確定レベルではありません。<a :href="link('/assess/howto.html')">評価の進め方</a>の手順で証拠を確認してください。</p>
      <div class="mm-actions">
        <button type="button" class="mm-button" @click="copy">{{ copied ? 'コピーしました' : '集計をMarkdownでコピー' }}</button>
        <button type="button" class="mm-button mm-button-danger" :disabled="selected.length === 0 && state.stage === null && !state.target" @click="clearAll">リセット</button>
      </div>
      <details class="mm-markdown"><summary>Markdownで表示</summary><pre data-testid="mm-markdown">{{ markdown }}</pre></details>
    </div>
  </section>
</template>
