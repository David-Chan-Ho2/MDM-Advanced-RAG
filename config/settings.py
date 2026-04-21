from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Paths ---
    RAW_DATA_DIR: Path = Path("data/raw")
    PROCESSED_DIR: Path = Path("data/processed")
    CHUNKS_DIR: Path = Path("data/chunks")
    EXPORTS_DIR: Path = Path("data/exports")
    BM25_INDEX_PATH: Path = Path("data/bm25_index.pkl")
    REVIEW_DB_PATH: str = "data/review.db"
    QDRANT_LOCAL_PATH: Path = Path("data/qdrant_local")

    # --- LLM ---
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_EXTRACTION_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_VALIDATION_MODEL: str = "claude-sonnet-4-6"

    # --- Embeddings ---
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 100
    EMBEDDING_DIMENSIONS: int = 384

    # --- Chunking ---
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # --- Retrieval ---
    TOP_K_DENSE: int = 10
    TOP_K_SPARSE: int = 10
    TOP_K_RERANK: int = 5
    HYBRID_CANDIDATE_POOL: int = 20
    RRF_K: int = 60  # Reciprocal Rank Fusion constant
    QUERY_DECOMPOSITION_MAX_SUBQUERIES: int = 4

    # --- Vector Store (Qdrant) ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "product_docs"

    # --- Batch Processing ---
    BATCH_CONCURRENCY: int = 5
    INDEX_FLUSH_BATCH_SIZE: int = 100
    MAX_RETRIES: int = 3

settings = Settings()
