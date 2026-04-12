FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Raspberry Pi / ARM64 is the default target; this image is multiplatform
# Build: docker buildx build --platform linux/arm64 -t marketcommand-api .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
