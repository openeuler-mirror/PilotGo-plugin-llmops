import os

from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL_ID = os.getenv("LLM_MODEL", "gpt-4o-mini")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
ROLE_MAP = {
    "system": "system",
    "user": "user",
    "assistant": "assistant",
    "tool": "tool",
    "model": "assistant",
}


def get_model(model_id: str | None = None) -> OpenAIChat:
    """Return an OpenAIChat model instance for the given model ID."""
    return OpenAIChat(
        id=model_id or DEFAULT_MODEL_ID,
        api_key=DEFAULT_API_KEY,
        base_url=DEFAULT_BASE_URL,
        role_map=ROLE_MAP,
        extra_body={"thinking": {"type": "disabled"}}
    )
