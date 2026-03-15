import { readdirSync, readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')   // registry root

export interface Issue {
  url: string
  title: string
  createdAt: string
}

export interface Consumer {
  repo: string
  repoUrl: string
  company: string
  status: 'passed' | 'failed'
  checkedAt: string | null
  issues: Issue[]
}

export interface Provider {
  name: string
  specType: string
}

export interface StatusData {
  consumers: Consumer[]
  providers: Provider[]
}

function walkJson(dir: string): string[] {
  if (!existsSync(dir)) return []
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walkJson(full))
    else if (entry.name.endsWith('.json')) out.push(full)
  }
  return out
}

export default {
  load(): StatusData {
    const consumerMap = new Map<string, Consumer>()

    // ── Pass records ────────────────────────────────────────────────────────
    const passDir = join(ROOT, 'companies/consumers/pass')
    for (const file of walkJson(passDir)) {
      if (!file.endsWith('status.json')) continue
      try {
        const rec = JSON.parse(readFileSync(file, 'utf-8'))
        consumerMap.set(rec.repo, {
          repo:      rec.repo,
          repoUrl:   rec.url,
          company:   rec.company,
          status:    'passed',
          checkedAt: rec.checked_at ?? null,
          issues:    [],
        })
      } catch {}
    }

    // ── Fail records ─────────────────────────────────────────────────────────
    // Path: fail/<owner>/<repo>/<issue-number>.json
    const failDir = join(ROOT, 'companies/consumers/fail')
    for (const file of walkJson(failDir)) {
      try {
        const rec = JSON.parse(readFileSync(file, 'utf-8'))
        const rel   = file.slice(failDir.length + 1)          // "owner/repo/123.json"
        const parts = rel.replace(/\\/g, '/').split('/')
        const repo  = `${parts[0]}/${parts[1]}`
        const issue: Issue = {
          url:       rec.url,
          title:     rec.title,
          createdAt: rec.created_at,
        }
        const existing = consumerMap.get(repo)
        if (existing) {
          existing.status = 'failed'
          existing.issues.push(issue)
        } else {
          consumerMap.set(repo, {
            repo,
            repoUrl:   `https://github.com/${repo}`,
            company:   rec.company,
            status:    'failed',
            checkedAt: rec.created_at,
            issues:    [issue],
          })
        }
      } catch {}
    }

    // Sort issues per consumer newest-first
    for (const c of consumerMap.values()) {
      c.issues.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      if (c.status === 'failed' && c.issues.length > 0) {
        c.checkedAt = c.issues[0].createdAt
      }
    }

    // ── Providers ────────────────────────────────────────────────────────────
    const providersDir = join(ROOT, 'companies/providers')
    const providers: Provider[] = []
    if (existsSync(providersDir)) {
      for (const entry of readdirSync(providersDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue
        const sub = readdirSync(join(providersDir, entry.name), { withFileTypes: true })
        const specType = sub.find(e => e.isDirectory())?.name ?? 'openapi'
        providers.push({ name: entry.name, specType })
      }
    }
    providers.sort((a, b) => a.name.localeCompare(b.name))

    const consumers = [...consumerMap.values()].sort((a, b) =>
      a.repo.localeCompare(b.repo)
    )

    return { consumers, providers }
  },
}
