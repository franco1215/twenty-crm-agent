import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM Provider
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    # Bedrock
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )

    # Twenty CRM
    twenty_crm_url: str = os.getenv("TWENTY_CRM_URL", "http://localhost:3000")
    twenty_api_key: str = os.getenv("TWENTY_API_KEY", "")

    # Web
    port: int = int(os.getenv("PORT", "3001"))

    def validate(self) -> None:
        if not self.twenty_api_key:
            raise ValueError("TWENTY_API_KEY is required. Get it from Twenty CRM Settings -> APIs & Webhooks")
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        if self.llm_provider not in ("anthropic", "bedrock"):
            raise ValueError(f"LLM_PROVIDER must be 'anthropic' or 'bedrock', got '{self.llm_provider}'")


config = Config()
