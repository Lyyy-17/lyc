/// <reference types="vite/client" />

declare module 'plotly.js-dist-min' {
  const Plotly: {
    react: (...args: unknown[]) => unknown
    relayout: (...args: unknown[]) => unknown
    restyle: (...args: unknown[]) => unknown
    Plots: { resize: (id: string) => unknown }
  }
  export default Plotly
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
