from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings


def get_llm() -> BaseChatModel:
    s = get_settings()
    return init_chat_model(
        s.llm_model,
        model_provider=s.llm_provider,
        temperature=s.llm_temperature,
        api_key=s.llm_api_key,
    )