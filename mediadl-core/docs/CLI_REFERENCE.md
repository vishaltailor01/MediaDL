# MediaDL Core - CLI Reference

The MediaDL CLI allows developers to quickly wrap media processing engines inside of CI/CD workflows, build bash automation scripts, and communicate directly with Remote Cloud Executors or run via `ffmpeg` natively.

**Help output available natively via**:
```bash
python3 cli/mediadl.py --help
```

---

## 1. Convert Commands

Converts a supported video formatting cleanly through our Engine wrapper.

**Local (Synchronous)**
```bash
python3 cli/mediadl.py convert input.mp4 --to mp3
```
*Creates `input.mp3` next to `input.mp4`.*

**Remote (Asynchronous Background Task)**
```bash
python3 cli/mediadl.py convert s3://bucket/test.mp4 --to mp3 --remote
```
Outputs a `jobId` for querying state.

---

## 2. Extract Commands
Simplified interface explicitly aimed at detaching `mp3` audio from complex video files natively.

```bash
python3 cli/mediadl.py extract input.mp4
# Local equivalent to convert --to mp3
```

---

## 3. Trim Commands
Cut segments directly deterministically through `-ss` and `-t` mapped features.

```bash
python3 cli/mediadl.py trim clip.mp4 --start 00:00:10 --duration 00:00:05 -o short-clip.mp4
```

---

## 4. Batching System
The `--remote` or Local engines are rapidly repeated across matching inputs deterministically. (Phase 2 Component)

```bash
python3 cli/mediadl.py batch convert ./asset-folder --ext .avi --to mp4
```

---

## 5. View Remote Task Status
```bash
python3 cli/mediadl.py status fd83c921-a4f6-4a41-aa6d...
```

*Expected JSON Output:*
```json
{
  "status": "completed",
  "request": {
    "type": "convert",
    "input": "s3://my-bucket/test.mp4",
    "outputFormat": "mp3",
    "trimStart": null,
    "trimDuration": null,
    "webhookUrl": null
  },
  "result": "s3://my-bucket/output.mp3",
  "error": null
}
```
