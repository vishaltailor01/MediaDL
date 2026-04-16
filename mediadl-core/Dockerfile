FROM python:3.10-slim

# Install system dependencies (ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy python dependencies and install
COPY mediadl-core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine and execution structure
COPY mediadl-core/ ./mediadl-core/

WORKDIR /app/mediadl-core

# Default execution is the API Server
# Can be overridden for worker deployment mapping
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
