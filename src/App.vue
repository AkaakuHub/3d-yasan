<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { DownloadOutline, ExpandOutline, OpenOutline } from '@vicons/ionicons5'
import {
  darkTheme,
  NButton,
  NCard,
  NConfigProvider,
  NEmpty,
  NIcon,
  NInput,
  NModal,
  NSkeleton,
  NSpace,
  NSelect,
} from 'naive-ui'
import catalogData from '../catalog.json'

type CatalogSourceItem = {
  title: string
  path: string
  format: string
  bytes: number
  source: string
  genre: string
  sha256: string
  page?: string
}

type CatalogVariant = Pick<CatalogSourceItem, 'source' | 'path' | 'page'>
type CatalogItem = Omit<CatalogSourceItem, 'source'> & { sources: string[]; variants: CatalogVariant[] }

type SortMode = 'num' | 'name' | 'big' | 'small'

const PAGE_SIZE = 48
const items = ref<CatalogItem[]>(deduplicateItems(catalogData.items))
const query = ref('')
const genre = ref<string | null>('')
const format = ref<string | null>('')
const source = ref<string | null>('')
const sort = ref<SortMode | null>('num')
const shown = ref(PAGE_SIZE)
const previewLoaded = ref(new Set<string>())
const previewError = ref(false)
const selected = ref<CatalogItem | null>(null)
const modalOpen = ref(false)
const loadingPaths = new Set<string>()
const uiTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? darkTheme : null
let viewerLoad: Promise<boolean> | undefined
let viewerUnavailable = false
let thumbObserver: IntersectionObserver | undefined

function deduplicateItems(data: CatalogSourceItem[]) {
  const uniqueItems = new Map<string, CatalogItem>()
  for (const item of data) {
    const existing = uniqueItems.get(item.sha256)
    if (existing) {
      if (!existing.sources.includes(item.source)) existing.sources.push(item.source)
      existing.variants.push({ source: item.source, path: item.path, page: item.page })
      continue
    }
    uniqueItems.set(item.sha256, {
      ...item,
      sources: [item.source],
      variants: [{ source: item.source, path: item.path, page: item.page }],
    })
  }
  return [...uniqueItems.values()]
}

const genres = computed(() => [...new Set(items.value.map(item => item.genre))].sort((a, b) => a.localeCompare(b, 'ja')))
const genreOptions = computed(() => [
  { label: 'ジャンル:すべて', value: '' },
  ...genres.value.map(itemGenre => ({ label: itemGenre, value: itemGenre })),
])
const formatOptions = [
  { label: '形式:すべて', value: '' },
  { label: 'GLB', value: 'GLB' },
  { label: 'FBX', value: 'FBX' },
]
const sourceOptions = [
  { label: '入手経路:すべて', value: '' },
  { label: 'REST', value: 'REST' },
  { label: 'Wayback', value: 'Wayback' },
]
const sortOptions = [
  { label: '番号順', value: 'num' },
  { label: '名前順', value: 'name' },
  { label: 'サイズ大きい順', value: 'big' },
  { label: 'サイズ小さい順', value: 'small' },
]
const filteredItems = computed(() => {
  const terms = query.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  const result = items.value.filter(item => {
    const haystack = `${item.title} ${item.genre} ${item.format}`.toLocaleLowerCase()
    return terms.every(term => haystack.includes(term))
      && (!genre.value || item.genre === genre.value)
      && (!format.value || item.format === format.value)
      && (!source.value || item.sources.includes(source.value))
  })
  return result.sort((a, b) => {
    if (sort.value === 'name') return a.title.localeCompare(b.title, 'ja')
    if (sort.value === 'big') return b.bytes - a.bytes
    if (sort.value === 'small') return a.bytes - b.bytes
    return (numberKey(a.title) - numberKey(b.title)) || a.title.localeCompare(b.title, 'ja')
  })
})
const visibleItems = computed(() => filteredItems.value.slice(0, shown.value))
const remaining = computed(() => Math.max(filteredItems.value.length - visibleItems.value.length, 0))

function numberKey(title: string) {
  const match = /^(\d+)/.exec(title)
  return match ? Number(match[1]) : 999999
}

function modelNumber(title: string) {
  return /^(\d+)/.exec(title)?.[1] ?? '—'
}

function modelName(title: string) {
  return title.replace(/^\d+[_\-\s]*/, '') || title
}

function loadViewer() {
  if (viewerUnavailable) return Promise.resolve(false)
  viewerLoad ??= import('@google/model-viewer')
    .then(() => true)
    .catch(() => {
      viewerUnavailable = true
      previewError.value = true
      return false
    })
  return viewerLoad
}

async function loadPreview(path: string) {
  if (previewLoaded.value.has(path) || loadingPaths.has(path)) return
  loadingPaths.add(path)
  if (await loadViewer()) previewLoaded.value = new Set(previewLoaded.value).add(path)
  loadingPaths.delete(path)
}

function observeThumbs() {
  thumbObserver?.disconnect()
  thumbObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      const path = entry.target.getAttribute('data-preview-path')
      if (path) void loadPreview(path)
      thumbObserver?.unobserve(entry.target)
    }
  }, { rootMargin: '320px 0px' })
  document.querySelectorAll<HTMLElement>('[data-preview-path]').forEach(element => thumbObserver?.observe(element))
}

async function openPreview(item: CatalogItem) {
  if (!(await loadViewer())) return
  selected.value = item
  modalOpen.value = true
}

function showMore() {
  shown.value += PAGE_SIZE
  void nextTick(observeThumbs)
}

watch([query, genre, format, source, sort], () => {
  shown.value = PAGE_SIZE
  void nextTick(observeThumbs)
})
watch(modalOpen, value => {
  if (!value) selected.value = null
})

onMounted(() => void nextTick(observeThumbs))
onUnmounted(() => thumbObserver?.disconnect())
</script>

<template>
  <n-config-provider :theme="uiTheme">
    <header class="site-header">
      <h1>3D屋さんarchive</h1>
    </header>

    <main class="page-content">
      <section class="hero">
        <h2>モデルを探す</h2>
      </section>

      <section class="controls" aria-label="検索と絞り込み">
        <n-input v-model:value="query" class="search-input" size="large" clearable placeholder="モデル名を検索（例: 椅子、ベッド、ランプ）" />
        <n-select v-model:value="genre" size="large" :options="genreOptions" placeholder="ジャンル" />
        <n-select v-model:value="format" size="large" :options="formatOptions" placeholder="形式" />
        <n-select v-model:value="source" size="large" :options="sourceOptions" placeholder="入手経路" />
        <n-select v-model:value="sort" size="large" :options="sortOptions" placeholder="並び順" />
      </section>

      <p class="count">{{ filteredItems.length }}件ヒット（{{ visibleItems.length }}件表示中）</p>

      <section v-if="visibleItems.length" class="grid" aria-label="モデル一覧">
        <n-card v-for="item in visibleItems" :key="item.sha256" class="card" :bordered="false" hoverable :content-style="{ padding: '0' }">
          <div v-if="item.format === 'GLB'" class="thumb" :data-preview-path="item.path">
            <model-viewer
              v-if="previewLoaded.has(item.path)"
              class="thumbnail-model"
              :src="item.path"
              :alt="item.title"
              interaction-prompt="none"
              loading="lazy"
              shadow-intensity="0.2"
            />
            <n-empty v-else-if="previewError" size="small" />
            <n-skeleton v-else text :repeat="3" />
          </div>
          <div v-else class="thumb thumb-empty" />

          <div class="card-body">
            <p class="model-id">モデル{{ modelNumber(item.title) }}</p>
            <h3>{{ modelName(item.title) }}</h3>
            <n-space :size="8" class="links">
              <n-button v-for="variant in item.variants" :key="variant.path" text type="primary" tag="a" :href="variant.path" download>
                <template #icon><n-icon><download-outline /></n-icon></template>
                {{ item.variants.length > 1 ? `${variant.source}からダウンロード` : 'ダウンロード' }}
              </n-button>
              <n-button v-if="item.format === 'GLB'" text type="primary" @click="openPreview(item)">
                <template #icon><n-icon><expand-outline /></n-icon></template>
                拡大表示
              </n-button>
              <template v-for="variant in item.variants" :key="`${variant.path}:page`">
                <n-button v-if="variant.page" text tag="a" :href="variant.page" target="_blank" rel="noopener">
                  <template #icon><n-icon><open-outline /></n-icon></template>
                  {{ item.variants.length > 1 ? `${variant.source}の元ページ` : '元ページ' }}
                </n-button>
              </template>
            </n-space>
          </div>
        </n-card>
      </section>
      <n-empty v-else description="条件に一致するモデルがありません" />

      <n-button v-if="remaining > 0" class="more" type="primary" secondary size="large" @click="showMore">もっと表示（残り{{ remaining }}件）</n-button>
    </main>

    <n-modal v-model:show="modalOpen" preset="card" class="preview-modal" :title="selected?.title" :bordered="false">
      <model-viewer
        v-if="selected"
        class="modal-model"
        :src="selected.path"
        :alt="selected.title"
        camera-controls
        interaction-prompt="none"
        shadow-intensity="0.2"
      />
    </n-modal>
  </n-config-provider>
</template>
