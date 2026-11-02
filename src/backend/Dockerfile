# Build
FROM python:3.12.15-slim AS build

WORKDIR /app

RUN python -m venv /opt/venv
COPY requirements.txt ./
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# Runtime
FROM python:3.12.15-slim AS runtime

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=build /opt/venv /opt/venv

# Includes the immutable .data directory; files are read only on explicit load.
COPY . ./
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
