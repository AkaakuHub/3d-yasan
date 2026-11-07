import vue from '@vitejs/plugin-vue'

export default {
  server: {
    port: 5173,
  },
  plugins: [vue({
    template: {
      compilerOptions: {
        isCustomElement: tag => tag === 'model-viewer',
      },
    },
  })],
}
