import { Type } from "@sinclair/typebox";
import yaml from "js-yaml";

const BASE = "https://raw.githubusercontent.com/DriftaBot/registry/main";

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.text();
}

interface SpecConfig {
  type: string;
  repo: string;
  path?: string;
  path_pattern?: string;
  output?: string;
  output_dir?: string;
}

interface CompanyConfig {
  name: string;
  display_name: string;
  specs: SpecConfig[];
}

interface Registry {
  companies: CompanyConfig[];
}

async function loadRegistry(): Promise<CompanyConfig[]> {
  const raw = await fetchText(`${BASE}/provider.companies.yaml`);
  const data = yaml.load(raw) as Registry;
  return data.companies ?? [];
}

export default function (api: any) {
  api.registerTool({
    name: "driftabot_list_providers",
    description:
      "List all API providers tracked in the DriftaBot Registry with their spec types and GitHub repos.",
    optional: true,
    parameters: Type.Object({
      filter: Type.Optional(
        Type.String({
          description: "Optional keyword to filter providers by name",
        })
      ),
    }),
    async execute(_id: string, { filter }: { filter?: string }) {
      const companies = await loadRegistry();
      const filtered = filter
        ? companies.filter(
            (c) =>
              c.name.toLowerCase().includes(filter.toLowerCase()) ||
              c.display_name.toLowerCase().includes(filter.toLowerCase())
          )
        : companies;

      const lines = filtered.map((c) => {
        const types = c.specs.map((s) => s.type).join(", ");
        const repos = c.specs.map((s) => s.repo).join(", ");
        return `- **${c.display_name}** (\`${c.name}\`): ${types} — ${repos}`;
      });

      return {
        content: [
          {
            type: "text",
            text: `## DriftaBot Providers (${filtered.length})\n\n${lines.join("\n")}`,
          },
        ],
      };
    },
  });

  api.registerTool({
    name: "driftabot_get_drift",
    description:
      "Get the latest API drift/breaking-change report for a specific provider from DriftaBot Registry.",
    optional: true,
    parameters: Type.Object({
      repo: Type.String({
        description:
          "GitHub org/repo of the provider (e.g. 'stripe/openapi', 'github/rest-api-description'). Find this from driftabot_list_providers.",
      }),
    }),
    async execute(_id: string, { repo }: { repo: string }) {
      const url = `${BASE}/drifts/${repo}/result.md`;
      try {
        const text = await fetchText(url);
        if (!text.trim()) {
          return {
            content: [
              {
                type: "text",
                text: `No breaking changes detected for \`${repo}\`.`,
              },
            ],
          };
        }
        return { content: [{ type: "text", text }] };
      } catch {
        return {
          content: [
            {
              type: "text",
              text: `No drift report found for \`${repo}\`. Either no breaking changes were detected since the last crawl, or this provider is not tracked.`,
            },
          ],
        };
      }
    },
  });

  api.registerTool({
    name: "driftabot_get_spec_info",
    description:
      "Get spec configuration details for a provider from DriftaBot Registry (spec type, GitHub repo, file paths).",
    optional: true,
    parameters: Type.Object({
      name: Type.String({
        description:
          "Provider slug or display name (e.g. 'stripe', 'github', 'twilio', 'Shopify')",
      }),
    }),
    async execute(_id: string, { name }: { name: string }) {
      const companies = await loadRegistry();
      const company = companies.find(
        (c) =>
          c.name.toLowerCase() === name.toLowerCase() ||
          c.display_name.toLowerCase() === name.toLowerCase()
      );

      if (!company) {
        return {
          content: [
            {
              type: "text",
              text: `Provider "${name}" not found in DriftaBot Registry. Use driftabot_list_providers to see all tracked providers.`,
            },
          ],
        };
      }

      const specs = company.specs
        .map(
          (s) =>
            `- **type:** ${s.type}\n  **repo:** ${s.repo}\n  **path:** ${s.path ?? s.path_pattern ?? "(directory)"}`
        )
        .join("\n");

      return {
        content: [
          {
            type: "text",
            text: `## ${company.display_name} (\`${company.name}\`)\n\n${specs}`,
          },
        ],
      };
    },
  });
}
