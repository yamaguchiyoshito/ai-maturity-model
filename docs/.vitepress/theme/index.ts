import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import MatrixAssessment from './MatrixAssessment.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('MatrixAssessment', MatrixAssessment)
  }
} satisfies Theme
