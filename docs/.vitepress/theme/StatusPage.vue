<template>
  <div class="status-page">

    <!-- Search -->
    <div class="sp-search-wrap">
      <input
        v-model="query"
        class="sp-search"
        placeholder="Search providers…"
        aria-label="Search"
      />
      <span v-if="query" class="sp-clear" @click="query = ''" title="Clear">✕</span>
    </div>

    <!-- ── Providers ──────────────────────────────────────────── -->
    <section class="sp-section">
      <h2 class="sp-section-title">
        Providers
        <span class="sp-count-title">{{ filteredProviders.length }}</span>
      </h2>
      <div v-if="filteredProviders.length" class="sp-provider-grid">
        <component
          :is="p.githubUrl ? 'a' : 'div'"
          v-for="p in filteredProviders"
          :key="p.name"
          :href="p.githubUrl ?? undefined"
          :target="p.githubUrl ? '_blank' : undefined"
          :rel="p.githubUrl ? 'noopener' : undefined"
          class="sp-provider-card"
        >
          <span class="sp-provider-name">{{ p.displayName }}</span>
          <span :class="['sp-badge', 'sp-badge--' + p.specType]">{{ p.specType }}</span>
        </component>
      </div>
      <p v-else class="sp-empty">No providers match your search.</p>
    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { StatusData } from '../../status.data'

const props = defineProps<{ data: StatusData }>()

const query = ref('')

const q = computed(() => query.value.trim().toLowerCase())

const filteredProviders = computed(() =>
  q.value
    ? props.data.providers.filter(p =>
        p.name.toLowerCase().includes(q.value) ||
        p.specType.toLowerCase().includes(q.value)
      )
    : props.data.providers
)
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
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s, background 0.2s;
}
a.sp-provider-card:hover {
  border-color: var(--vp-c-brand-1);
  background: var(--vp-c-bg-elv);
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

/* ── Dark mode overrides ─────────────────────────────────────── */
.dark .sp-badge--openapi { background: #1e3a5f; color: #93c5fd; }
.dark .sp-badge--graphql { background: #500724; color: #f9a8d4; }
.dark .sp-badge--grpc    { background: #14532d; color: #86efac; }
</style>
