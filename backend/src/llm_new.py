import os
from typing import TypedDict, Optional

ProviderInfo = TypedDict("ProviderInfo", {
    "provider": str,   # "openai" | "azure" | "mock"
    "model_label": str # what router should place in X-Llm-Model
})

openai_client = None  # Will hold OpenAI() or AzureOpenAI() instance
provider_info: ProviderInfo = {"provider": "mock", "model_label": "mock"}

def _has_openai_env() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))

def _has_azure_env() -> bool:
    return all([
        os.environ.get("AZURE_OPENAI_API_KEY"),
        os.environ.get("AZURE_OPENAI_ENDPOINT")
    ])

def _init_openai_native():
    # OpenAI SDK >=1.x
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    label = os.environ.get("OPENAI_MODEL_LABEL", "gpt-4o-mini")
    return client, {"provider": "openai", "model_label": label}

def _init_openai_azure():
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    )
    # For Azure, the "model" label we expose should be the deployment name
    label = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    return client, {"provider": "azure", "model_label": label}

try:
    if _has_openai_env():
        openai_client, provider_info = _init_openai_native()
    elif _has_azure_env():
        openai_client, provider_info = _init_openai_azure()
    else:
        # mock fallback (keep None and provider_info="mock")
        pass
except Exception as e:
    # If client init fails, stay on mock but make it visible
    print(f"[llm] Failed to init real LLM client, using mock. Error: {e}")
    openai_client = None
    provider_info = {"provider": "mock", "model_label": "mock"}
