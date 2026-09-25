# FactChat Backend

FactChat is an agentic RAG backend for scientific paper research. It fetches papers from arXiv, parses PDFs with Docling, embeds content with FastEmbed, stores vectors in Milvus, and answers questions through a multi-agent LangGraph pipeline powered by OpenAI models.

## Stack

- **API**: FastAPI · Python 3.12
- **Parsing**: Docling (PDF → chunks, tables, figures)
- **Embeddings**: FastEmbed with `BAAI/bge-small-en-v1.5`
- **Vector DB**: Milvus via `pymilvus`
- **Agents**: LangGraph `StateGraph` + LangChain `ChatOpenAI`
- **Core agents** (`gpt-5-nano`): Retriever, Repo, Refetch, Recommendation
- **Callable agents** (`gpt-5-mini`): `@buddy`, `@review`, `@writer`
- **Answer model** (`gpt-5-mini`): Final RAG-grounded synthesis

## Project layout

```text
app/
  agents/             # LangGraph agent pipeline (coordinator, graph, nodes)
  api/                # FastAPI routes and dependency injection
  core/               # Config, logging, shared exceptions
  embeddings/         # FastEmbed service
  ingestion/          # Paper ingestion pipeline and status tracking
  llm/                # Legacy OpenRouter / Groq services
  models/             # Pydantic request/response and domain schemas
  parsers/            # Docling PDF parser with reference extraction
  retrieval/          # Hybrid vector search service
  services/           # arXiv client, paper discovery, session management
  storage/            # Filesystem storage (permanent + temp session files)
  utils/              # Text helpers, ID generation, DOCX generation, sandbox
  vectorstores/       # Milvus store with dynamic session collection lifecycle
storage/              # Runtime data (not committed)
  papers/             # Permanent paper storage
  temp/               # Session-scoped temporary files (auto-cleaned)
tests/                # Unit and integration tests
docker-compose.yml
Dockerfile
requirements.txt
```

## Environment

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY` — **required** for the agent pipeline
- `MILVUS_URI` / `MILVUS_TOKEN` — vector database connection
- `OPENAI_AGENT_MODEL` / `OPENAI_CHAT_MODEL` — model overrides (optional)

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run with Docker

```bash
docker compose up --build
```

The compose stack includes:
- **backend** — FactChat API (port 8000)
- **milvus** — vector database (port 19530)
- **etcd** — Milvus metadata store
- **minio** — Milvus object storage (console on port 9001)

The backend waits for Milvus to be healthy before starting. Both services include healthchecks.

## API surface

### Session lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/sessions` | Start a new learning session (topic → classify → ingest 15 papers) |
| `POST` | `/chat/query` | Query the agent pipeline (auto-enriched with session context) |
| `POST` | `/chat/sessions/{id}/end` | Merge vectors to global DB, drop session collections, clean temp files |

### Paper discovery & ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/papers/search` | Search arXiv for papers |
| `POST` | `/papers/latest` | Fetch latest arXiv papers |
| `POST` | `/papers/ingest` | Ingest papers into the vector store |
| `GET`  | `/papers/ingest/{job_id}` | Check ingestion job status |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | API and Milvus connectivity check |

## Example requests

Start a learning session:

```bash
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"topic": "attention mechanisms in transformers"}'
```

Ask a question (with session context):

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How does multi-head attention improve performance?", "session_id": "<session_id>"}'
```

Use a callable agent:

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "@buddy write a PyTorch self-attention implementation", "session_id": "<session_id>"}'
```

End a session:

```bash
curl -X POST http://localhost:8000/chat/sessions/<session_id>/end
```

## Architecture notes

- **Session isolation**: Each session creates `sess_{id}_chunks`, `sess_{id}_tables`, `sess_{id}_figures` collections in Milvus. On session end, vectors merge into `global_{category}_*` collections.
- **Topic classification**: Automatic categorization (ai, healthcare, social, law, general) via LLM with keyword fallback.
- **Agent pipeline**: LangGraph `StateGraph` with conditional edges for refetch loops and `@agent` branching.
- **Transparent refetch**: If retrieval scores fall below 0.65, the Refetch Agent auto-ingests 1–2 new papers without interrupting the conversation.
- **Duplicate handling**: Deterministic checks on `paper_id`, `arxiv_id`, `doi`, and `title_hash`.
- **Temp storage**: Session PDFs download to `storage/temp/{session_id}/` and are auto-deleted on session end.

## Testing

```bash
python -m unittest discover -s tests -v
```

## Operational notes

- Docling parsing is CPU-heavy and runs in worker threads to avoid blocking the event loop.
- If `OPENAI_API_KEY` is not set, the agent pipeline will raise `RuntimeError` on startup.
- The `storage/` directory is mounted as a volume in Docker and should not be committed.
