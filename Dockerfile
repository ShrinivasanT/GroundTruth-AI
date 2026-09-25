# ── Stage 1: builder ───────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# Heavy ML / parsing wheels are installed in their own layer so
# incremental rebuilds only re-run the lightweight pip install.
# We explicitly install the CPU-only version of PyTorch to drastically reduce
# the download size (from ~2.5GB to ~150MB) and prevent timeouts / memory crashes.
RUN pip install --no-cache-dir --timeout=300 --retries=10 \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --timeout=300 --retries=10 \
    transformers \
    docling \
    fastembed

RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Minimal runtime packages (curl for healthchecks, vim for debug shells).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

COPY . .

# Ensure runtime artefact directories exist inside the container.
RUN mkdir -p storage/papers storage/temp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
