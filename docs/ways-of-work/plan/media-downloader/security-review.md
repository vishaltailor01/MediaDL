# Security Review

## Threat Model
- No user accounts, but input URLs could be malicious
- Backend runs shell commands (yt-dlp, FFmpeg)
- Potential for abuse (DDoS, spam, scraping)

## OWASP Top 10
- A1: Injection — Sanitize all inputs, validate URLs
- A2: Broken Auth — N/A (no auth)
- A3: Sensitive Data Exposure — No PII stored
- A4: XML External Entities — N/A
- A5: Broken Access Control — N/A
- A6: Security Misconfiguration — Harden server, minimal dependencies
- A7: XSS — Escape all output, CSP headers
- A8: Insecure Deserialization — N/A
- A9: Components with Known Vulns — Keep yt-dlp, FFmpeg, Python up to date
- A10: Insufficient Logging — Log errors, not user data

## LLM Top 10
- Prompt injection: N/A
- Data leakage: N/A
- Model abuse: N/A

## Zero Trust
- No trust in user input
- Minimal attack surface
- No persistent user data

## Priority Issues
- Input validation
- Shell command sanitization
- Rate limiting
- Monitoring for abuse