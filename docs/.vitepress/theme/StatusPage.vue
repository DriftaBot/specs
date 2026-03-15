<template>
  <div class="status-page">

    <!-- Search -->
    <div class="sp-search-wrap">
      <input
        v-model="query"
        class="sp-search"
        placeholder="Search providers and consumers…"
        aria-label="Search"
      />
      <span v-if="query" class="sp-clear" @click="query = ''" title="Clear">✕</span>
    </div>

    <!-- Tabs -->
    <div class="sp-tabs" role="tablist">
      <button
        v-for="t in TABS"
        :key="t.id"
        role="tab"
        :class="['sp-tab', { active: tab === t.id }]"
        @click="tab = t.id"
      >
        {{ t.label }}
        <span class="sp-count">{{ t.count }}</span>
      </button>
    </div>

    <!-- ── Providers ──────────────────────────────────────────── -->
    <section v-if="tab !== 'consumers'" class="sp-section">
      <h2 class="sp-section-title">
        Providers
        <span class="sp-count-title">{{ filteredProviders.length }}</span>
      </h2>
      <div v-if="filteredProviders.length" class="sp-provider-grid">
        <div
          v-for="p in filteredProviders"
          :key="p.name"
          class="sp-provider-card"
        >
          <span class="sp-provider-name">{{ p.name }}</span>
          <span :class="['sp-badge', 'sp-badge--' + p.specType]">{{ p.specType }}</span>
        </div>
      </div>
      <p v-else class="sp-empty">No providers match your search.</p>
    </section>

    <!-- ── Consumers ─────────────────────────────────────────── -->
    <section v-if="tab !== 'providers'" class="sp-section">
      <h2 class="sp-section-title">
        Consumers
        <span class="sp-count-title">{{ filteredConsumers.length }}</span>
      </h2>

      <div v-if="filteredConsumers.length" class="sp-table-wrap">
        <table class="sp-table">
          <thead>
            <tr>
              <th>Repository</th>
              <th>Provider</th>
              <th>Status</th>
              <th>Last checked</th>
              <th>Issues</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in filteredConsumers"
              :key="c.repo"
              :class="c.status === 'failed' ? 'sp-row--fail' : 'sp-row--pass'"
            >
              <td>
                <a :href="c.repoUrl" target="_blank" rel="noopener">{{ c.repo }}</a>
              </td>
              <td>{{ c.company }}</td>
              <td>
                <span :class="['sp-status', 'sp-status--' + c.status]">
                  {{ c.status === 'passed' ? '✓ Passed' : '✗ Failed' }}
                </span>
              </td>
              <td class="sp-date">{{ c.checkedAt ? formatDate(c.checkedAt) : '—' }}</td>
              <td>
                <span v-if="!c.issues.length" class="sp-no-issues">—</span>
                <span v-else class="sp-issue-list">
                  <a
                    v-for="issue in c.issues"
                    :key="issue.url"
                    :href="issue.url"
                    :title="issue.title"
                    target="_blank"
                    rel="noopener"
                    class="sp-issue-link"
                  >#{{ issueNum(issue.url) }}</a>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="sp-empty">No consumers match your search.</p>
    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { StatusData } from '../../status.data'

const props = defineProps<{ data: StatusData }>()

const query = ref('')
const tab   = ref<'all' | 'providers' | 'consumers'>('all')

const TABS = computed(() => [
  { id: 'all'       as const, label: 'All',       count: props.data.providers.length + props.data.consumers.length },
  { id: 'providers' as const, label: 'Providers', count: props.data.providers.length },
  { id: 'consumers' as const, label: 'Consumers', count: props.data.consumers.length },
])

const q = computed(() => query.value.trim().toLowerCase())

const filteredProviders = computed(() =>
  q.value
    ? props.data.providers.filter(p =>
        p.name.toLowerCase().includes(q.value) ||
        p.specType.toLowerCase().includes(q.value)
      )
    : props.data.providers
)

const filteredConsumers = computed(() =>
  q.value
    ? props.data.consumers.filter(c =>
        c.repo.toLowerCase().includes(q.value) ||
        c.company.toLowerCase().includes(q.value) ||
        c.status.includes(q.value)
      )
    : props.data.consumers
)

function formatDate(iso: string): string {
  const d = new Date(iso)
  const day   = d.getUTCDate()
  const month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getUTCMonth()]
  const year  = d.getUTCFullYear()
  let   hours = d.getUTCHours()
  const mins  = String(d.getUTCMinutes()).padStart(2, '0')
  const ampm  = hours >= 12 ? 'pm' : 'am'
  hours = hours % 12 || 12
  return `${day} ${month} ${year} ${hours}:${mins} ${ampm}`
}

function issueNum(url: string): string {
  return url.split('/').pop() ?? '?'
}
</script>

<style scoped>
.status-page {
  margin-top: 1.5rem;
}

/* ── Search ─────────────────────────────────────────────────── */
.sp-search-wrap {
  position: relative;
  margin-bottom: 1.25rem;
}
.sp-search {
  width: 100%;
  padding: 0.55rem 2.2rem 0.55rem 0.85rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.sp-search:focus {
  border-color: var(--vp-c-brand-1);
}
.sp-clear {
  position: absolute;
  right: 0.7rem;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--vp-c-text-3);
  font-size: 0.8rem;
  user-select: none;
}
.sp-clear:hover { color: var(--vp-c-text-1); }

/* ── Tabs ────────────────────────────────────────────────────── */
.sp-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.75rem;
  border-bottom: 1px solid var(--vp-c-divider);
}
.sp-tab {
  padding: 0.4rem 0.9rem 0.55rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  color: var(--vp-c-text-2);
  font-size: 0.9rem;
  transition: color 0.2s, border-color 0.2s;
  margin-bottom: -1px;
}
.sp-tab:hover { color: var(--vp-c-text-1); }
.sp-tab.active {
  color: var(--vp-c-brand-1);
  border-bottom-color: var(--vp-c-brand-1);
  font-weight: 500;
}
.sp-count {
  margin-left: 0.35rem;
  font-size: 0.75rem;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  padding: 0.05rem 0.4rem;
  border-radius: 10px;
  color: var(--vp-c-text-2);
}

/* ── Section ─────────────────────────────────────────────────── */
.sp-section { margin-bottom: 2.5rem; }
.sp-section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--vp-c-text-1);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  padding: 0;
}
.sp-count-title {
  font-size: 0.78rem;
  background: var(--vp-c-bg-mute);
  padding: 0.1rem 0.45rem;
  border-radius: 10px;
  color: var(--vp-c-text-2);
  font-weight: 400;
}
.sp-empty {
  color: var(--vp-c-text-3);
  font-size: 0.9rem;
}

/* ── Provider grid ───────────────────────────────────────────── */
.sp-provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.6rem;
}
.sp-provider-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  gap: 0.5rem;
}
.sp-provider-name {
  font-size: 0.85rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Badges ──────────────────────────────────────────────────── */
.sp-badge {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
.sp-badge--openapi { background: #dbeafe; color: #1d4ed8; }
.sp-badge--graphql { background: #fce7f3; color: #be185d; }
.sp-badge--grpc    { background: #dcfce7; color: #15803d; }

/* ── Consumer table ──────────────────────────────────────────── */
.sp-table-wrap { overflow-x: auto; }
.sp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.sp-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: var(--vp-c-bg-soft);
  border-bottom: 2px solid var(--vp-c-divider);
  color: var(--vp-c-text-2);
  font-weight: 600;
  white-space: nowrap;
}
.sp-table td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--vp-c-divider);
  vertical-align: middle;
}
.sp-table a {
  color: var(--vp-c-brand-1);
  text-decoration: none;
}
.sp-table a:hover { text-decoration: underline; }

/* ── Status badges ───────────────────────────────────────────── */
.sp-status {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.15rem 0.55rem;
  border-radius: 12px;
  white-space: nowrap;
}
.sp-status--passed { background: #dcfce7; color: #15803d; }
.sp-status--failed { background: #fee2e2; color: #b91c1c; }

/* ── Date cell ───────────────────────────────────────────────── */
.sp-date {
  white-space: nowrap;
  color: var(--vp-c-text-2);
  font-size: 0.82rem;
}

/* ── Issue links ─────────────────────────────────────────────── */
.sp-issue-list { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.sp-issue-link {
  font-size: 0.8rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: #fef3c7;
  color: #92400e !important;
  text-decoration: none !important;
  border: 1px solid #fde68a;
  white-space: nowrap;
}
.sp-issue-link:hover { background: #fde68a; }
.sp-no-issues { color: var(--vp-c-text-3); }

/* ── Dark mode overrides ─────────────────────────────────────── */
.dark .sp-badge--openapi { background: #1e3a5f; color: #93c5fd; }
.dark .sp-badge--graphql { background: #500724; color: #f9a8d4; }
.dark .sp-badge--grpc    { background: #14532d; color: #86efac; }
.dark .sp-status--passed { background: #14532d; color: #86efac; }
.dark .sp-status--failed { background: #450a0a; color: #fca5a5; }
.dark .sp-issue-link     { background: #451a03; color: #fcd34d !important; border-color: #78350f; }
.dark .sp-issue-link:hover { background: #78350f; }
</style>
