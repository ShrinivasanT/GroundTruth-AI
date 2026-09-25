# Repository Guidelines

## Project Structure & Module Organization
This repository is a FastAPI backend for paper ingestion and retrieval. Core code lives in `app/`, organized by concern:

- `app/api/` for route handlers and dependency wiring
- `app/core/` for config, logging, and shared exceptions
- `app/ingestion/`, `app/retrieval/`, `app/vectorstores/`, `app/embeddings/`, and `app/llm/` for pipeline stages
- `app/models/` for request and response schemas
- `app/services/` and `app/parsers/` for external integrations and document parsing

Runtime artifacts belong under `storage/` and should not be committed. Keep ad hoc scripts in `scripts/`.

## Build, Test, and Development Commands

- `python -m venv .venv` and `.venv\Scripts\Activate.ps1` create and activate a local environment.
- `pip install -r requirements.txt` installs the backend dependencies.
- `uvicorn app.main:app --reload` runs the API locally with auto-reload.
- `docker compose up --build` starts the containerized stack.
- `python API_test.py` is a manual smoke check for the arXiv fetch flow.

## Coding Style & Naming Conventions
Use Python 3.12, 4-space indentation, and standard snake_case for functions, modules, and files. Use PascalCase for classes and Pydantic models. Keep route handlers thin and push business logic into service modules. Prefer explicit type hints and small, focused functions. Match existing naming patterns such as `get_settings()`, `paper_service.py`, and `SearchPapersRequest`.

## Testing Guidelines
No formal automated test framework is configured yet. If you add tests, place them in `tests/` and name files `test_*.py`. Keep test names descriptive and prefer async-aware tests for API and pipeline code. Validate changes with focused smoke tests against `GET /health` and the relevant paper or chat endpoint before opening a PR.

## Commit & Pull Request Guidelines
There is no existing commit history to mirror, so use short, imperative commit subjects such as `Add ingestion status validation`. For pull requests, include:

- a short summary of the change
- any environment or config updates
- sample requests or responses for API changes
- screenshots only when documentation or generated assets change

## Security & Configuration Tips
Copy `.env.example` to `.env` and keep API keys, Milvus credentials, and other secrets out of version control. Check `app/core/config.py` before adding new settings so new environment variables have safe defaults.
