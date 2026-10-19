from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    hf_token: str = ""
    base_model: str = "codellama/CodeLlama-7b-hf"

    chroma_persist_dir: str = "./data/chromadb"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    prometheus_port: int = 8000
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
