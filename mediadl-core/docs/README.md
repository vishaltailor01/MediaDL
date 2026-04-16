# MediaDL Core - Documentation

Welcome to **MediaDL Core**, a headless, composable media processing engine designed for automation-first developers. It enables you to run deterministic media workflows locally, within CI/CD pipelines, or in robust cloud environments.

## Table of Contents

1. [Quickstart](#quickstart)
2. [Architecture](#architecture)
3. [CLI Reference](./CLI_REFERENCE.md)
4. [API Reference](./API_REFERENCE.md)
5. [AWS Fargate Deployment](./DEPLOYMENT.md)
6. [SDKs](#sdks)

## Quickstart

### 1. Requirements
Ensure you have the following installed if testing locally:
- Python 3.10+
- `ffmpeg` (In your system PATH)

### 2. Setup
```bash
git clone https://github.com/vishaltailor01/MediaDL.git
cd MediaDL/mediadl-core
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Running the Development Server
If you intend on sending jobs to the Background Task API (`--remote` processes), boot the API:
```bash
uvicorn api.main:app --reload
```

## Architecture

MediaDL Core is separated into three robust layers:
- **CLI / SDK Layer**: Acts as the interface for scriptability.
- **API Server Layer**: Takes jobs dynamically, storing execution configuration in Amazon DynamoDB.
- **Compute Layer**: Runs `FfmpegEngine` safely in temporary sandboxes, downloading from & uploading directly to `s3://` targets. Requires an explicit AWS Configuration via standard environment variables or IAM Identity Profiles.

## SDKs

For deep integrations alongside Phase 2 configurations, use the provided language wrappers:
*   [Node.js SDK Reference](../sdk-node/README.md)
*   [Java SDK Details](../sdk-java/README.md)
