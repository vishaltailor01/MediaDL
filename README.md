# MediaDL
An Open-Source Media Processing Engine & Downloader Toolkit

## 📖 Overview
MediaDL is a robust repository housing two distinct architectural layers designed to solve complex media challenges for completely different use cases:

1. **`mediadl-core/`**: A headless, composable media processing engine designed specifically for **backend engineers, DevOps, and CI/CD pipelines**. It provides deterministic, automation-first media execution—completely bypassing UI-driven friction.
2. **`backend/`**: A standalone, localized FastAPI instance designed for consumer-level integrations, featuring local URL blocklisting and YouTube playlist integrations.

This repository heavily favours developer-first operations over simple GUIs.

---

## ⚡ 1. MediaDL Core (`/mediadl-core`)
*"A reliable, scriptable media processing engine for automation-first developers."*

MediaDL Core standardises API workflows for media pipelines. It functions strictly to make CI/CD media processing testable and reproducible, working phenomenally in containerised remote workers (AWS Fargate) and serverless environments.

### Core Features
- **Unified Interfaces**: Access the exact same deterministic FFmpeg configurations via **CLI**, **REST API**, or our **SDKs** (Node.js & Java).
- **Asynchronous Job System**: State-tracked queue processing via SQS / DynamoDB structures (Queued -> Processing -> Completed/Failed).
- **S3 Standardised**: Direct `s3://bucket/` input and output resolution mapped natively.
- **Enterprise Config Tolerances**: Config-based limits (`mediadl.config.json`) mapped against payload sizes and sandbox timeouts.
- **Webhooks**: Event-driven responses eliminating the need for continuous polling.
- **Plugin Ecosystem**: Inject custom Python logic (e.g., Watermarking, Metadata injection) safely into the execution pipeline dynamically.

### Navigation Links
- [MediaDL Core Quickstart & Overview](./mediadl-core/README.md)
- [API Reference](./mediadl-core/docs/API_REFERENCE.md)
- [CLI Reference](./mediadl-core/docs/CLI_REFERENCE.md)
- [Swagger OpenAPI JSON](./mediadl-core/docs/swagger.json)

---

## 🔧 2. Standard Backend Server (`/backend`)
A legacy monolithic approach containing immediate `yt-dlp` scraping implementations alongside `ffmpeg` execution. 

This branch executes directly with local threading architectures rather than distributed decoupling logic. It is highly experimental and suited exclusively for direct-action tests or single-user environments.

---

## 🏗️ Architecture Models
MediaDL supports scaling from a single laptop up to a massive Fargate cluster naturally.
It incorporates native Docker configurations to ensure dependency consistency across FFmpeg builds.

To view an example layout of the distributed AWS-oriented Docker deployment, look at:
[`/mediadl-core/docker-compose.yml`](./mediadl-core/docker-compose.yml)

Or review GitHub action templates for implementing automated asset pipelines here:
[`/mediadl-core/examples/ci-cd/github-action.yml`](./mediadl-core/examples/ci-cd/github-action.yml)

---

## License
Provided natively under the **MIT License**.
See [LICENSE](./LICENSE) for details.
