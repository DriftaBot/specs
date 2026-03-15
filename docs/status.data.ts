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
  displayName: string
  specType: string
  githubUrl: string | null
}

export interface StatusData {
  consumers: Consumer[]
  providers: Provider[]
}

/**
 * Parse provider.companies.yaml line-by-line to extract name → githubUrl and displayName.
 * Reads the first `repo:` entry under each company's `specs:` block.
 */
function loadProviderMeta(): Map<string, { displayName: string; githubUrl: string }> {
  const yamlPath = join(ROOT, 'provider.companies.yaml')
  if (!existsSync(yamlPath)) return new Map()

  const map = new Map<string, { displayName: string; githubUrl: string }>()
  let name = ''
  let displayName = ''
  let inSpecs = false

  for (const raw of readFileSync(yamlPath, 'utf-8').split('\n')) {
    const line = raw.trimEnd()
    // New company entry:  "  - name: stripe"
    const nameMatch = line.match(/^ {2}- name:\s+(.+)/)
    if (nameMatch) { name = nameMatch[1].trim(); displayName = ''; inSpecs = false; continue }

    const dnMatch = line.match(/^ {4}display_name:\s+(.+)/)
    if (dnMatch && name) { displayName = dnMatch[1].trim(); continue }

    if (/^ {4}specs:/.test(line)) { inSpecs = true; continue }

    if (inSpecs && name && !map.has(name)) {
      const repoMatch = line.match(/repo:\s+(.+)/)
      if (repoMatch) {
        map.set(name, {
          displayName: displayName || name,
          githubUrl: `https://github.com/${repoMatch[1].trim()}`,
        })
        inSpecs = false
      }
    }
  }
  return map
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
    const meta        = loadProviderMeta()
    const providersDir = join(ROOT, 'companies/providers')
    const providers: Provider[] = []
    if (existsSync(providersDir)) {
      for (const entry of readdirSync(providersDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue
        const sub      = readdirSync(join(providersDir, entry.name), { withFileTypes: true })
        const specType = sub.find(e => e.isDirectory())?.name ?? 'openapi'
        const m        = meta.get(entry.name)
        providers.push({
          name:        entry.name,
          displayName: m?.displayName ?? entry.name,
          specType,
          githubUrl:   m?.githubUrl ?? null,
        })
      }
    }
    providers.sort((a, b) => a.name.localeCompare(b.name))

    const consumers = [...consumerMap.values()].sort((a, b) =>
      a.repo.localeCompare(b.repo)
    )

    return { consumers, providers }
  },
}
