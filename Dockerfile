# Streamlit app image. Ollama is NOT containerised: the model server stays on
# the host so it keeps the GPU, and the container reaches it through
# OLLAMA_HOST (see docker-compose.yml).
#
# Python 3.12 rather than 3.14: torch and its dependencies still ship 3.12
# wheels, so the build stays a download rather than a compile.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl is only for the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, so code edits don't invalidate the (large) wheel layer.
# CPU-only torch first: the container only embeds queries (all-MiniLM-L6-v2) and
# the GPU stays with Ollama on the host, so PyPI's default CUDA build would add
# several GB of unused libraries. requirements.txt then finds torch installed.
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install -r requirements.txt

# Application code and the assets it reads at runtime.
COPY src/ ./src/
COPY narratives/ ./narratives/
COPY sources/TYPOLOGY_MAPPING.md ./sources/TYPOLOGY_MAPPING.md
COPY .streamlit/ ./.streamlit/

# chroma_db/, data/, generated/ and audit_logs/ are bind-mounted by compose —
# they are built by the pipeline scripts, not baked into the image.

EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true"]
