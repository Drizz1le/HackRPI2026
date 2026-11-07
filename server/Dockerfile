FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Build context is the repo root (see compose.yaml) so the prompt files in
# qwen/ can be copied into the image.
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/*.py ./
COPY qwen/ ./qwen/
COPY fixtures/ ./fixtures/

# Default: run as a searcher (subagent). compose overrides this per service.
CMD ["python", "worker.py"]
