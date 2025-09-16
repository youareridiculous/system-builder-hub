"""
Privacy Modes & Data Governance v1
Defines privacy modes and their configuration for SBH.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class PrivacyMode(Enum):
    """Privacy modes for SBH deployment."""
    LOCAL_ONLY = "local_only"
    BYO_KEYS = "byo_keys"
    PRIVATE_CLOUD = "private_cloud"


@dataclass
class PrivacyConfig:
    """Configuration for a privacy mode."""
    mode: PrivacyMode
    allowlist_domains: Set[str]
    prompt_retention_seconds: int
    response_retention_seconds: int
    log_redaction_enabled: bool
    third_party_calls_allowed: bool
    cmk_required: bool
    description: str


class PrivacyModeResolver:
    """Resolves privacy mode configurations."""
    
    def __init__(self):
        self._configs = self._initialize_configs()
    
    def _initialize_configs(self) -> Dict[PrivacyMode, PrivacyConfig]:
        """Initialize default configurations for each privacy mode."""
        return {
            PrivacyMode.LOCAL_ONLY: PrivacyConfig(
                mode=PrivacyMode.LOCAL_ONLY,
                allowlist_domains=set(),  # No outbound calls by default
                prompt_retention_seconds=0,  # No retention
                response_retention_seconds=0,  # No retention
                log_redaction_enabled=True,  # Always redact
                third_party_calls_allowed=False,  # Block all third-party calls
                cmk_required=False,  # Local encryption only
                description="Local-only mode: No external calls, no data retention"
            ),
            PrivacyMode.BYO_KEYS: PrivacyConfig(
                mode=PrivacyMode.BYO_KEYS,
                allowlist_domains={
                    "api.openai.com",
                    "api.anthropic.com", 
                    "api.aws.ai",
                    "api.cohere.ai",
                    "api.perplexity.ai",
                    "api.groq.com",
                    "api.together.xyz",
                    "api.mistral.ai",
                    "api.deepseek.com",
                    "api.ollama.ai",
                    "api.llama-api.com",
                    "api.vertex.ai",
                    "api.bedrock-runtime.us-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-west-2.amazonaws.com",
                    "api.bedrock-runtime.eu-west-1.amazonaws.com",
                    "api.bedrock-runtime.ap-southeast-1.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-1.amazonaws.com",
                    "api.bedrock-runtime.ca-central-1.amazonaws.com",
                    "api.bedrock-runtime.eu-central-1.amazonaws.com",
                    "api.bedrock-runtime.ap-south-1.amazonaws.com",
                    "api.bedrock-runtime.sa-east-1.amazonaws.com",
                    "api.bedrock-runtime.eu-north-1.amazonaws.com",
                    "api.bedrock-runtime.me-south-1.amazonaws.com",
                    "api.bedrock-runtime.af-south-1.amazonaws.com",
                    "api.bedrock-runtime.ap-east-1.amazonaws.com",
                    "api.bedrock-runtime.eu-west-2.amazonaws.com",
                    "api.bedrock-runtime.eu-west-3.amazonaws.com",
                    "api.bedrock-runtime.eu-south-1.amazonaws.com",
                    "api.bedrock-runtime.me-central-1.amazonaws.com",
                    "api.bedrock-runtime.ap-southeast-2.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-2.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-3.amazonaws.com",
                    "api.bedrock-runtime.us-gov-west-1.amazonaws.com",
                    "api.bedrock-runtime.us-gov-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-iso-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-isob-east-1.amazonaws.com",
                    "api.bedrock-runtime.cn-north-1.amazonaws.com.cn",
                    "api.bedrock-runtime.cn-northwest-1.amazonaws.com.cn",
                    "email.us-east-1.amazonaws.com",  # AWS SES
                    "email.us-west-2.amazonaws.com",
                    "email.eu-west-1.amazonaws.com",
                    "email.ap-southeast-1.amazonaws.com",
                    "email.ap-northeast-1.amazonaws.com",
                    "email.ca-central-1.amazonaws.com",
                    "email.eu-central-1.amazonaws.com",
                    "email.ap-south-1.amazonaws.com",
                    "email.sa-east-1.amazonaws.com",
                    "email.eu-north-1.amazonaws.com",
                    "email.me-south-1.amazonaws.com",
                    "email.af-south-1.amazonaws.com",
                    "email.ap-east-1.amazonaws.com",
                    "email.eu-west-2.amazonaws.com",
                    "email.eu-west-3.amazonaws.com",
                    "email.eu-south-1.amazonaws.com",
                    "email.me-central-1.amazonaws.com",
                    "email.ap-southeast-2.amazonaws.com",
                    "email.ap-northeast-2.amazonaws.com",
                    "email.ap-northeast-3.amazonaws.com",
                    "email.us-gov-west-1.amazonaws.com",
                    "email.us-gov-east-1.amazonaws.com",
                    "email.us-iso-east-1.amazonaws.com",
                    "email.us-isob-east-1.amazonaws.com",
                    "email.cn-north-1.amazonaws.com.cn",
                    "email.cn-northwest-1.amazonaws.com.cn",
                    "s3.amazonaws.com",  # AWS S3
                    "s3.us-east-1.amazonaws.com",
                    "s3.us-west-2.amazonaws.com",
                    "s3.eu-west-1.amazonaws.com",
                    "s3.ap-southeast-1.amazonaws.com",
                    "s3.ap-northeast-1.amazonaws.com",
                    "s3.ca-central-1.amazonaws.com",
                    "s3.eu-central-1.amazonaws.com",
                    "s3.ap-south-1.amazonaws.com",
                    "s3.sa-east-1.amazonaws.com",
                    "s3.eu-north-1.amazonaws.com",
                    "s3.me-south-1.amazonaws.com",
                    "s3.af-south-1.amazonaws.com",
                    "s3.ap-east-1.amazonaws.com",
                    "s3.eu-west-2.amazonaws.com",
                    "s3.eu-west-3.amazonaws.com",
                    "s3.eu-south-1.amazonaws.com",
                    "s3.me-central-1.amazonaws.com",
                    "s3.ap-southeast-2.amazonaws.com",
                    "s3.ap-northeast-2.amazonaws.com",
                    "s3.ap-northeast-3.amazonaws.com",
                    "s3.us-gov-west-1.amazonaws.com",
                    "s3.us-gov-east-1.amazonaws.com",
                    "s3.us-iso-east-1.amazonaws.com",
                    "s3.us-isob-east-1.amazonaws.com",
                    "s3.cn-north-1.amazonaws.com.cn",
                    "s3.cn-northwest-1.amazonaws.com.cn",
                    "slack.com",  # Slack
                    "hooks.slack.com",
                    "api.slack.com",
                    "googleapis.com",  # Google APIs
                    "www.googleapis.com",
                    "oauth2.googleapis.com",
                    "accounts.google.com",
                    "github.com",  # GitHub
                    "api.github.com",
                    "raw.githubusercontent.com",
                    "gist.github.com",
                    "gitlab.com",  # GitLab
                    "api.gitlab.com",
                    "bitbucket.org",  # Bitbucket
                    "api.bitbucket.org",
                    "notion.so",  # Notion
                    "api.notion.com",
                    "linear.app",  # Linear
                    "api.linear.app",
                    "clickup.com",  # ClickUp
                    "api.clickup.com",
                    "asana.com",  # Asana
                    "app.asana.com",
                    "api.asana.com",
                    "trello.com",  # Trello
                    "api.trello.com",
                    "jira.com",  # Jira
                    "api.atlassian.com",
                    "monday.com",  # Monday.com
                    "api.monday.com",
                    "airtable.com",  # Airtable
                    "api.airtable.com",
                    "zapier.com",  # Zapier
                    "hooks.zapier.com",
                    "api.zapier.com",
                    "n8n.io",  # n8n
                    "api.n8n.io",
                    "make.com",  # Make (Integromat)
                    "api.make.com",
                    "pipedream.com",  # Pipedream
                    "api.pipedream.com",
                    "webhook.site",  # Webhook testing
                    "httpbin.org",  # HTTP testing
                    "jsonplaceholder.typicode.com",  # JSON testing
                    "postman-echo.com",  # Postman Echo
                    "mockapi.io",  # MockAPI
                    "mocky.io",  # Mocky
                    "httpstat.us",  # HTTP status testing
                },
                prompt_retention_seconds=0,  # No retention
                response_retention_seconds=0,  # No retention
                log_redaction_enabled=True,  # Always redact
                third_party_calls_allowed=True,  # Allow with tenant keys
                cmk_required=True,  # Require CMK for tenant keys
                description="Bring Your Own Keys: Tenant-provided API keys, no data retention"
            ),
            PrivacyMode.PRIVATE_CLOUD: PrivacyConfig(
                mode=PrivacyMode.PRIVATE_CLOUD,
                allowlist_domains={
                    "api.openai.com",
                    "api.anthropic.com",
                    "api.aws.ai",
                    "api.cohere.ai",
                    "api.perplexity.ai",
                    "api.groq.com",
                    "api.together.xyz",
                    "api.mistral.ai",
                    "api.deepseek.com",
                    "api.ollama.ai",
                    "api.llama-api.com",
                    "api.vertex.ai",
                    "api.bedrock-runtime.us-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-west-2.amazonaws.com",
                    "api.bedrock-runtime.eu-west-1.amazonaws.com",
                    "api.bedrock-runtime.ap-southeast-1.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-1.amazonaws.com",
                    "api.bedrock-runtime.ca-central-1.amazonaws.com",
                    "api.bedrock-runtime.eu-central-1.amazonaws.com",
                    "api.bedrock-runtime.ap-south-1.amazonaws.com",
                    "api.bedrock-runtime.sa-east-1.amazonaws.com",
                    "api.bedrock-runtime.eu-north-1.amazonaws.com",
                    "api.bedrock-runtime.me-south-1.amazonaws.com",
                    "api.bedrock-runtime.af-south-1.amazonaws.com",
                    "api.bedrock-runtime.ap-east-1.amazonaws.com",
                    "api.bedrock-runtime.eu-west-2.amazonaws.com",
                    "api.bedrock-runtime.eu-west-3.amazonaws.com",
                    "api.bedrock-runtime.eu-south-1.amazonaws.com",
                    "api.bedrock-runtime.me-central-1.amazonaws.com",
                    "api.bedrock-runtime.ap-southeast-2.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-2.amazonaws.com",
                    "api.bedrock-runtime.ap-northeast-3.amazonaws.com",
                    "api.bedrock-runtime.us-gov-west-1.amazonaws.com",
                    "api.bedrock-runtime.us-gov-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-iso-east-1.amazonaws.com",
                    "api.bedrock-runtime.us-isob-east-1.amazonaws.com",
                    "api.bedrock-runtime.cn-north-1.amazonaws.com.cn",
                    "api.bedrock-runtime.cn-northwest-1.amazonaws.com.cn",
                    "email.us-east-1.amazonaws.com",  # AWS SES
                    "email.us-west-2.amazonaws.com",
                    "email.eu-west-1.amazonaws.com",
                    "email.ap-southeast-1.amazonaws.com",
                    "email.ap-northeast-1.amazonaws.com",
                    "email.ca-central-1.amazonaws.com",
                    "email.eu-central-1.amazonaws.com",
                    "email.ap-south-1.amazonaws.com",
                    "email.sa-east-1.amazonaws.com",
                    "email.eu-north-1.amazonaws.com",
                    "email.me-south-1.amazonaws.com",
                    "email.af-south-1.amazonaws.com",
                    "email.ap-east-1.amazonaws.com",
                    "email.eu-west-2.amazonaws.com",
                    "email.eu-west-3.amazonaws.com",
                    "email.eu-south-1.amazonaws.com",
                    "email.me-central-1.amazonaws.com",
                    "email.ap-southeast-2.amazonaws.com",
                    "email.ap-northeast-2.amazonaws.com",
                    "email.ap-northeast-3.amazonaws.com",
                    "email.us-gov-west-1.amazonaws.com",
                    "email.us-gov-east-1.amazonaws.com",
                    "email.us-iso-east-1.amazonaws.com",
                    "email.us-isob-east-1.amazonaws.com",
                    "email.cn-north-1.amazonaws.com.cn",
                    "email.cn-northwest-1.amazonaws.com.cn",
                    "s3.amazonaws.com",  # AWS S3
                    "s3.us-east-1.amazonaws.com",
                    "s3.us-west-2.amazonaws.com",
                    "s3.eu-west-1.amazonaws.com",
                    "s3.ap-southeast-1.amazonaws.com",
                    "s3.ap-northeast-1.amazonaws.com",
                    "s3.ca-central-1.amazonaws.com",
                    "s3.eu-central-1.amazonaws.com",
                    "s3.ap-south-1.amazonaws.com",
                    "s3.sa-east-1.amazonaws.com",
                    "s3.eu-north-1.amazonaws.com",
                    "s3.me-south-1.amazonaws.com",
                    "s3.af-south-1.amazonaws.com",
                    "s3.ap-east-1.amazonaws.com",
                    "s3.eu-west-2.amazonaws.com",
                    "s3.eu-west-3.amazonaws.com",
                    "s3.eu-south-1.amazonaws.com",
                    "s3.me-central-1.amazonaws.com",
                    "s3.ap-southeast-2.amazonaws.com",
                    "s3.ap-northeast-2.amazonaws.com",
                    "s3.ap-northeast-3.amazonaws.com",
                    "s3.us-gov-west-1.amazonaws.com",
                    "s3.us-gov-east-1.amazonaws.com",
                    "s3.us-iso-east-1.amazonaws.com",
                    "s3.us-isob-east-1.amazonaws.com",
                    "s3.cn-north-1.amazonaws.com.cn",
                    "s3.cn-northwest-1.amazonaws.com.cn",
                    "slack.com",  # Slack
                    "hooks.slack.com",
                    "api.slack.com",
                    "googleapis.com",  # Google APIs
                    "www.googleapis.com",
                    "oauth2.googleapis.com",
                    "accounts.google.com",
                    "github.com",  # GitHub
                    "api.github.com",
                    "raw.githubusercontent.com",
                    "gist.github.com",
                    "gitlab.com",  # GitLab
                    "api.gitlab.com",
                    "bitbucket.org",  # Bitbucket
                    "api.bitbucket.org",
                    "notion.so",  # Notion
                    "api.notion.com",
                    "linear.app",  # Linear
                    "api.linear.app",
                    "clickup.com",  # ClickUp
                    "api.clickup.com",
                    "asana.com",  # Asana
                    "app.asana.com",
                    "api.asana.com",
                    "trello.com",  # Trello
                    "api.trello.com",
                    "jira.com",  # Jira
                    "api.atlassian.com",
                    "monday.com",  # Monday.com
                    "api.monday.com",
                    "airtable.com",  # Airtable
                    "api.airtable.com",
                    "zapier.com",  # Zapier
                    "hooks.zapier.com",
                    "api.zapier.com",
                    "n8n.io",  # n8n
                    "api.n8n.io",
                    "make.com",  # Make (Integromat)
                    "api.make.com",
                    "pipedream.com",  # Pipedream
                    "api.pipedream.com",
                    "webhook.site",  # Webhook testing
                    "httpbin.org",  # HTTP testing
                    "jsonplaceholder.typicode.com",  # JSON testing
                    "postman-echo.com",  # Postman Echo
                    "mockapi.io",  # MockAPI
                    "mocky.io",  # Mocky
                    "httpstat.us",  # HTTP status testing
                },
                prompt_retention_seconds=86400,  # 24 hours default
                response_retention_seconds=86400,  # 24 hours default
                log_redaction_enabled=True,  # Always redact
                third_party_calls_allowed=True,  # Allow with platform keys
                cmk_required=True,  # Require CMK for encryption
                description="Private Cloud: Platform-managed with strict redaction and short retention"
            )
        }
    
    def get_config(self, mode: PrivacyMode) -> PrivacyConfig:
        """Get configuration for a privacy mode."""
        return self._configs[mode]
    
    def is_domain_allowed(self, mode: PrivacyMode, domain: str) -> bool:
        """Check if a domain is allowed for a privacy mode."""
        config = self.get_config(mode)
        return domain in config.allowlist_domains
    
    def get_retention_config(self, mode: PrivacyMode) -> tuple[int, int]:
        """Get retention configuration for a privacy mode."""
        config = self.get_config(mode)
        return config.prompt_retention_seconds, config.response_retention_seconds
    
    def requires_cmk(self, mode: PrivacyMode) -> bool:
        """Check if a privacy mode requires CMK."""
        config = self.get_config(mode)
        return config.cmk_required
    
    def allows_third_party_calls(self, mode: PrivacyMode) -> bool:
        """Check if a privacy mode allows third-party calls."""
        config = self.get_config(mode)
        return config.third_party_calls_allowed


# Global resolver instance
privacy_resolver = PrivacyModeResolver()
