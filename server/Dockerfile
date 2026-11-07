FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY coord.py worker.py ./

# Default: run as a worker. The coordinator overrides this with `python coord.py`.
CMD ["python", "worker.py"]
