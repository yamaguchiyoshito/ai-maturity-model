<script setup lang="ts">
import { ref, onMounted } from 'vue'

/**
 * 左の目次を「開く／閉じる」。閉じると切替ボタンだけが残り、成熟度マトリクスのような横長の表に本文の幅を使える。
 * 選択は localStorage に保存し、config.ts の head スクリプトが描画前に html[data-sidebar] へ適用する。デスクトップ幅でだけ表示する。
 */
const KEY = 'ai-maturity.sidebar'
const closed = ref(false)
function apply() {
  document.documentElement.dataset.sidebar = closed.value ? 'closed' : 'open'
  try { localStorage.setItem(KEY, closed.value ? 'closed' : 'open') } catch { /* プライベートモード等では保存しない */ }
}
function toggle() { closed.value = !closed.value; apply() }
onMounted(() => { closed.value = document.documentElement.dataset.sidebar === 'closed' })
</script>

<template>
  <button type="button" class="sidebar-toggle" :class="{ closed }" :aria-pressed="closed" :aria-label="closed ? '目次を開く' : '目次を閉じる'" :title="closed ? '目次を開く' : '目次を閉じる'" @click="toggle">
    <span class="sidebar-toggle-icon" aria-hidden="true">{{ closed ? '»' : '«' }}</span><span class="sidebar-toggle-text">目次を閉じる</span>
  </button>
</template>
