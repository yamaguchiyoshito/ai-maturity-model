import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { h } from 'vue'
import MatrixAssessment from './MatrixAssessment.vue'
import SidebarToggle from './SidebarToggle.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  // 左の目次の先頭に「目次を閉じる」ボタンを置く（SidebarToggle.vue）
  Layout: () => h(DefaultTheme.Layout, null, { 'sidebar-nav-before': () => h(SidebarToggle) }),
  enhanceApp({ app }) {
    app.component('MatrixAssessment', MatrixAssessment)
  }
} satisfies Theme
