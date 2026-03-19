import { readdirSync, readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')   // registry root

export interface Provider {
  name: string
  displayName: string
  specType: string
  githubUrl: string | null
}

export interface StatusData {
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

export default {
  load(): StatusData {
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

    return { providers }
  },
}
