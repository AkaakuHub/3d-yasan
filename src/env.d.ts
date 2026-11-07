/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<Record<string, never>, Record<string, never>, never>
  export default component
}

declare module '*.css' {
  const styles: Record<string, string>
  export default styles
}
