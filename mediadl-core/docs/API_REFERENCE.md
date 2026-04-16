# MediaDL Core - Detailed API Documentation

## Overview
The MediaDL Core API is a RESTful service providing headless orchestration for complex media processing tasks. Built with FastAPI, it offers asynchronous job queues, execution tracking, and automatic webhook notifications. It enforces a strict stateless model; tracking happens via DynamoDB or local memory fallback arrays.

**Base URL**: `http://localhost:8000` (Locally testing via uvicorn)

---

## 1. Endpoints

### 1.1 Health Check / Root
Checks if the API server is alive.

- **URL**: `/`
- **Method**: `GET`
- **Success Response**:
  - **Code**: `200 OK`
  - **Content**:
    ```json
    {
      "message": "Welcome to MediaDL Core API. Post jobs to /jobs or check /docs for Swagger UI!"
    }
    ```

---

### 1.2 Create Processing Job
Submits a new automated media task. Jobs are queued and processed asynchronously in isolated sandboxes.

- **URL**: `/jobs`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`

#### Request Body Schema
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `type` | `string` | **Yes** | The operation to perform. Supported values: `convert`, `extract_audio`, `trim`. |
| `input` | `string` | **Yes** | The source media path. Can be an AWS S3 URI (`s3://bucket/file.mp4`) or an accessible container local absolute path. |
| `outputFormat` | `string` | **Yes** | The target media extension (e.g., `mp3`, `mp4`). |
| `trimStart` | `string` | Optional | Start timestamp for `trim` jobs. Format: `HH:MM:SS` (e.g. `00:00:15`). |
| `trimDuration`| `string` | Optional | Duration for `trim` jobs. Format: `HH:MM:SS` (e.g. `00:01:00`). |
| `webhookUrl` | `string` | Optional | HTTP URL to receive a POST request upon job completion or failure. |

#### Example: Video Conversion (cURL)
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "convert",
    "input": "s3://my-cloud-bucket/raw_video.mov",
    "outputFormat": "mp4",
    "webhookUrl": "https://api.myplatform.com/webhooks/mediadl"
  }'
```

#### Example: Audio Extraction
```json
{
  "type": "extract_audio",
  "input": "/app/mediadl-core/assets/interview.mp4",
  "outputFormat": "mp3"
}
```

#### Success Response
- **Code**: `200 OK`
- **Content**:
  ```json
  {
    "jobId": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
    "status": "queued"
  }
  ```

#### Error Responses
- **Code**: `422 Unprocessable Entity` (Invalid JSON schema or missing fields).

---

### 1.3 Get Job Status
Retrieves the real-time execution state of a previously submitted job.

- **URL**: `/jobs/{jobId}`
- **Method**: `GET`

#### URL Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `jobId` | `string` | **Yes** | The unique UUID identifying the job. |

#### Success Response
- **Code**: `200 OK`
- **Content**:
  ```json
  {
    "status": "completed",
    "request": {
      "type": "convert",
      "input": "s3://my-cloud-bucket/raw_video.mov",
      "outputFormat": "mp4",
      "trimStart": null,
      "trimDuration": null,
      "webhookUrl": "https://api.myplatform.com/webhooks/mediadl"
    },
    "result": "s3://my-cloud-bucket/raw_video.mp4",
    "error": null
  }
  ```

#### Job Status Lifecycle Transitions
- `queued`: Initially registered, waiting in SQS/Background task pool.
- `processing`: Engine has allocated the sandbox and begun downloading or running FFMpeg.
- `completed`: Operations finished, outputs delivered successfully.
- `failed`: System-level error, invalid input resolution, or FFmpeg crash.

#### Error Responses
- **Code**: `404 Not Found` (Job ID does not exist in local memory fallback or DynamoDB table).

---

## 2. Webhooks

Webhooks provide an event-driven mechanism avoiding constant REST polling against `/jobs/{jobId}`.

### Payload Delivery
When a job enters a terminal state (`completed` or `failed`), MediaDL natively sends an HTTP `POST` request to your provided `webhookUrl` with the following JSON signature:

```json
{
  "jobId": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "status": "completed",
  "result": "s3://my-cloud-bucket/raw_video.mp4",
  "error": null
}
```

*Note: Delivery is attempted with a 5-second timeout requirement preventing locking. If the receiving endpoint is unavailable, the webhook POST is safely dropped organically.*

---

## 3. Storage Integrations & Data Delivery

### S3 Resolution Protocol
If `input` begins with `s3://`, MediaDL Core automatically leverages the assumed AWS IAM Role / injected Environment Variable configurations:
1. The engine parses the Bucket and Key, downloading the file explicitly to an internal ephemeral Temporary Directory limits constraints.
2. It processes the asset strictly disconnected without network-lag overhead blocking rendering threads.
3. Automatically derives the Output Bucket-URI mapping to the source file name and expected `outputFormat` (e.g., `s3://bucket/episode1.mov` -> `s3://bucket/episode1.mp4`).
4. Executes the remote bucket upload.
5. Purges all localized temp environments safely out of the standard memory structures avoiding container storage swelling mapping out execution bounds.

### Local Disk Resolution
If given an absolute path (i.e. `/assets/video.mp4`), MediaDL relies exclusively on file/volume mounting mappings logically available internally to the Docker processing instance. Avoid relative pointers in scaled setups.
