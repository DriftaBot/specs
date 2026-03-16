"""
Run spec diffs for all changed specs and write results to drifts/.

Scans companies/providers/ vs /tmp/specs-before/ to find changed specs,
looks up the provider repo from provider.companies.yaml, and invokes
the driftabot CLI via subprocess with no shell interpolation.
"""
import os
import re
import subprocess
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PROVIDERS_DIR = REPO_ROOT / "companies" / "providers"
BEFORE_DIR = Path("/tmp/specs-before")
COMPANIES_YAML = REPO_ROOT / "provider.companies.yaml"

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]+$")


def _load_repo_map() -> dict[str, str]:
    """Return {provider_name: first_repo} from provider.companies.yaml."""
    with open(COMPANIES_YAML) as f:
        data = yaml.safe_load(f)
    repo_map: dict[str, str] = {}
    for company in data.get("companies", []):
        name = company.get("name", "")
        for spec in company.get("specs", []):
            repo = spec.get("repo", "")
            if repo:
                repo_map[name] = repo
                break
    return repo_map


def main() -> None:
    drifts_dir = REPO_ROOT / "drifts"
    drifts_dir.mkdir(exist_ok=True)

    repo_map = _load_repo_map()

    spec_exts = {".json", ".yaml", ".yml", ".proto"}
    for new_spec in PROVIDERS_DIR.rglob("*"):
        if not new_spec.is_file():
            continue
        if new_spec.suffix not in spec_exts:
            continue

        rel = new_spec.relative_to(PROVIDERS_DIR)
        old_spec = BEFORE_DIR / rel

        if not old_spec.exists():
            continue

        # Compare file contents; skip if identical
        if new_spec.read_bytes() == old_spec.read_bytes():
            continue

        # Path pattern: <name>/<spec_type>/<file>
        parts = rel.parts
        if len(parts) < 3:
            print(f"  [skip] unexpected path structure: {rel}")
            continue

        name = parts[0]
        spec_type = parts[1]

        # Validate name — must not contain path traversal or shell-special chars
        if not _SAFE_NAME_RE.match(name) or ".." in name:
            print(f"  [skip] unsafe provider name: {name!r}")
            continue

        repo = repo_map.get(name)
        if not repo:
            print(f"  [skip] no repo found for provider: {name}")
            continue

        if "/" not in repo:
            print(f"  [skip] malformed repo value for {name}: {repo!r}")
            continue

        org, repo_name = repo.split("/", 1)

        if spec_type not in ("openapi", "graphql", "grpc"):
            print(f"  [skip] unknown spec type: {spec_type}")
            continue

        out_dir = drifts_dir / org / repo_name
        out_dir.mkdir(parents=True, exist_ok=True)
        result_path = out_dir / "result.json"

        print(f"  [diff] {name} ({spec_type}): {old_spec} -> {new_spec}")

        result = subprocess.run(
            ["driftabot", spec_type, "--base", str(old_spec), "--head", str(new_spec), "--format", "json"],
            capture_output=True,
        )
        result_path.write_bytes(result.stdout)
        print(f"  [saved] {result_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
