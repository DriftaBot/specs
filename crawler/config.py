from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel


REPO_ROOT = Path(__file__).parent.parent
COMPANIES_YAML = REPO_ROOT / "provider.companies.yaml"
CONSUMERS_YAML = REPO_ROOT / "consumer.companies.yaml"


class SpecConfig(BaseModel):
    type: str  # "openapi" | "graphql" | "grpc"
    repo: str  # "owner/repo"
    path: Optional[str] = None          # single file path within repo
    path_pattern: Optional[str] = None  # directory to list and fetch all files from
    output: Optional[str] = None        # single output file path (relative to repo root)
    output_dir: Optional[str] = None    # output directory for path_pattern results


class ConsumerConfig(BaseModel):
    query: str  # GitHub Code Search query string


class CompanyConfig(BaseModel):
    name: str
    display_name: str
    specs: List[SpecConfig]
    consumers: List[ConsumerConfig] = []


class CompaniesRegistry(BaseModel):
    companies: List[CompanyConfig]


class RegisteredConsumer(BaseModel):
    repo: str                       # "owner/repo"
    companies: List[str]            # company names from companies.yaml
    contact: Optional[str] = None   # optional contact email


class ConsumerRegistry(BaseModel):
    consumers: List[RegisteredConsumer] = []


def load_registry() -> CompaniesRegistry:
    with open(COMPANIES_YAML) as f:
        data = yaml.safe_load(f)
    return CompaniesRegistry.model_validate(data)


def load_consumer_registry() -> ConsumerRegistry:
    if not CONSUMERS_YAML.exists():
        return ConsumerRegistry()
    with open(CONSUMERS_YAML) as f:
        data = yaml.safe_load(f) or {}
    return ConsumerRegistry.model_validate(data)
