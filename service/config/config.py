"""
Varve configuration.

Central place to define which LLM model powers the reasoning layer,
plus the other environment-driven settings the backend needs.

Import from this file everywhere instead of hardcoding model strings
or reading os.environ directly in multiple places — if you need to
swap models (e.g. for cost, speed, or a new release), change it here once.
"""

import os
from dotenv import load_dotenv

# Load .env file from project/service root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)


# --- NVIDIA API / DeepSeek Model selection ---
MODEL_INVOKE_URL = os.environ.get(
    "MODEL_INVOKE_URL",
    "https://integrate.api.nvidia.com/v1",
)
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-ai/deepseek-v4-flash")
MODEL_MAX_TOKENS = int(os.environ.get("MODEL_MAX_TOKENS", "16384"))
MODEL_TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "1.0"))
MODEL_TOP_P = float(os.environ.get("MODEL_TOP_P", "0.95"))
MODEL_SEED = int(os.environ.get("MODEL_SEED", "42"))

# API Key for authentication (e.g. "Bearer nvapi-...")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY")


# --- DataHub connection ---
DATAHUB_GMS_URL = os.environ.get("DATAHUB_GMS_URL") or "http://localhost:8080"
DATAHUB_GMS_TOKEN = os.environ.get("DATAHUB_GMS_TOKEN") or None  # optional for local quickstart


# --- Postgres connection ---
POSTGRES_DSN = os.environ.get(
    "VARVE_POSTGRES_DSN",
    "postgresql://varve:varve@localhost:5433/varve",
)


def validate_config() -> None:
    """
    Call this once at backend startup. Fails loudly and immediately
    rather than letting a missing key surface as a confusing error
    three layers deep during the demo.
    """
    missing = []
    if not MODEL_API_KEY:
        missing.append("MODEL_API_KEY")
    if not DATAHUB_GMS_URL:
        missing.append("DATAHUB_GMS_URL")

    if missing:
        raise RuntimeError(
            f"Missing required config: {', '.join(missing)}. "
            f"Set these as environment variables before starting the backend."
        )

    print(f"[config] LLM model:   {MODEL_NAME}")
    print(f"[config] Invoke URL:  {MODEL_INVOKE_URL}")
    print(f"[config] DataHub GMS: {DATAHUB_GMS_URL}")
    print(f"[config] Postgres:    {POSTGRES_DSN}")