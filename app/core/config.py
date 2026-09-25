from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    data_dir: Path = Field(default=Path("storage"))
    request_timeout_seconds: float = Field(default=45.0)
    http_max_connections: int = Field(default=20)
    http_max_keepalive_connections: int = Field(default=10)

    arxiv_base_url: HttpUrl = Field(default="http://export.arxiv.org/api/query")

    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    embedding_dimension: int = Field(default=384)
    embedding_batch_size: int = Field(default=32)

    milvus_uri: str = Field(default="http://milvus:19530")
    milvus_token: str = Field(default="root:Milvus")
    milvus_consistency_level: str = Field(default="Strong")
    milvus_papers_collection: str = Field(default="papers")
    milvus_chunks_collection: str = Field(default="paper_chunks")
    milvus_tables_collection: str = Field(default="paper_tables")
    milvus_figures_collection: str = Field(default="paper_figures")

    groq_api_key: str | None = Field(default=None)
    groq_model: str = Field(default="openai/gpt-oss-20b")
    groq_keyword_model: str = Field(default="meta-llama/llama-4-scout-17b-16e-instruct")

    huggingface_papers_api_url: HttpUrl = Field(default="https://huggingface.co/api/papers/search")

    openai_api_key: str | None = Field(default=None)
    openai_agent_model: str = Field(default="gpt-5-nano")
    openai_chat_model: str = Field(default="gpt-5-mini")
    refetch_relevance_threshold: float = Field(default=0.65)
    refetch_paper_limit: int = Field(default=2)

    openrouter_api_key: str | None = Field(default=None)
    openrouter_base_url: HttpUrl = Field(default="https://openrouter.ai/api/v1")
    openrouter_model: str = Field(default="openai/gpt-4o-mini")
    openrouter_http_referer: str | None = Field(default=None)
    openrouter_app_title: str | None = Field(default=None)

    ingestion_concurrency: int = Field(default=3)
    enrichment_concurrency: int = Field(default=4)
    max_search_results: int = Field(default=10)
    max_context_items: int = Field(default=12)
    chunk_size_chars: int = Field(default=1400)
    chunk_overlap_chars: int = Field(default=180)

    @property
    def papers_storage_dir(self) -> Path:
        return self.data_dir / "papers"

    @property
    def temp_storage_dir(self) -> Path:
        return self.data_dir / "temp"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
