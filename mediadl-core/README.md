# MediaDL Core

**MediaDL Core** is a headless, composable media processing engine designed specifically for backend engineers, DevOps, and CI/CD pipelines. It provides deterministic, automation-first media execution—completely bypassing UI-driven friction.

![MediaDL Core Architecture](https://img.shields.io/badge/Architecture-Serverless%20%7C%20Container-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen)

## 📌 Vision & Positioning
*"A reliable, scriptable media processing engine for automation-first developers."*

MediaDL Core is **not** a media downloading platform or UI-dashboard. It is a strict media execution engine designed to:
- Standardise API workflows for media pipelines.
- Make CI/CD media processing testable and reproducible.
- Function reliably in local testing, containerised remote workers (AWS Fargate), and serverless environments.

---

## ⚡ Features
- **Unified Interfaces**: Access the exact same deterministic FFmpeg configurations via **CLI**, **REST API**, or our **SDKs** (Node.js & Java).
- **Asynchronous Job System**: State-tracked queue processing (Queued -> Processing -> Completed/Failed).
- **S3 Standardised**: Direct `s3://bucket/` input and output resolution mapped natively.
- **Enterprise Config Tolerances**: Config-based limits (`mediadl.config.json`) mapped against payload sizes and sandbox timeouts.
- **Webhooks**: Event-driven responses eliminating the need for continuous polling.
- **Plugin Ecosystem**: Inject custom Python logic (e.g., Watermarking, Metadata injection) safely into the execution pipeline dynamically.

---

## 🚀 Quickstart (Local)

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg** installed and accessible in your system `$PATH`

### 2. Installation
```bash
git clone https://github.com/vishaltailor01/MediaDL.git
cd MediaDL/mediadl-core

# Setup Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

### 3. Run the Development Server
Boot the FastAPI server to expose endpoints and Swagger UI automatically:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
> **Swagger UI Access:** Visit `http://localhost:8000/docs` to interact visually with the API endpoint configurations.

### 4. CLI Execution
Convert a file locally using exact Engine configurations:
```bash
python3 cli/mediadl.py convert input.mp4 --to mp3
```

Dispatch an async remote queue job directly matching the API:
```bash
python3 cli/mediadl.py convert s3://my-bucket/test.mp4 --to mp3 --remote
```

---

## 🏗️ Architecture

MediaDL Core is layered to map heavily onto resilient Cloud Infrastructures:
1. **Storage Layer**: Uses AWS S3 for binary blobs. Configs and Job States live in Amazon DynamoDB.
2. **Compute Layer Option A (Queue)**: Decoupled `sqs` messages fetched by heavy Fargate FFmpeg polling workers (`workers/main.py`).
3. **Compute Layer Option B (Sync)**: Direct `BackgroundTasks` attached to FastAPI instances for lightweight operation execution.

---

## 📚 Documentation Directory
Dive deeper into specific components using our official docs:
- [API Reference](./docs/API_REFERENCE.md)
- [CLI Reference](./docs/CLI_REFERENCE.md)
- [Swagger OpenAPI JSON](./docs/swagger.json)
- CI/CD Action Template: [`examples/ci-cd/github-action.yml`](./examples/ci-cd/github-action.yml)

## 🤝 SDKs
Phase 2 language-specific integrations to integrate into your existing products immediately:
- [`@mediadl-core/sdk`](./sdk-node/README.md) - Node.js
- `com.mediadl:mediadl-core-sdk` - Java / Maven

## License
MIT License. See [LICENSE](LICENSE) for details.
