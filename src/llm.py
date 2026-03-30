from langchain_core.language_models.chat_models import BaseChatModel
from src.config import config


def get_llm() -> BaseChatModel:
    if config.llm_provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model=config.bedrock_model_id,
            region_name=config.aws_region,
            temperature=0,
        )
    else:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.anthropic_model,
            api_key=config.anthropic_api_key,
            temperature=0,
            max_tokens=4096,
        )
