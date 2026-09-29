# Backend API image. Build context is the repository root (needs requirements.txt).
#
# Installs the core runtime only — the VLM runs with the "mock" backend here.
# A GPU image with requirements-vlm.txt is added when the real model lands (Phase 1).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app

# Uploads/results live on a volume outside the code path (§29).
RUN useradd --create-home --uid 1000 vigraph \
    && mkdir -p /data/storage \
    && chown vigraph:vigraph /data/storage
ENV VIGRAPH_STORAGE_DIR=/data/storage
USER vigraph

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
