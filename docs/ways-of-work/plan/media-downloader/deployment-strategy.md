# Deployment Strategy

## Infrastructure
- Backend: Docker container (FastAPI, yt-dlp, FFmpeg)
- Frontend: Static files on CDN (Vercel, Netlify, or S3)
- Domain: Custom domain (e.g., mediadl.app)

## CI/CD
- GitHub Actions for build/test/deploy
- Linting, unit tests, browser tests
- Auto-deploy on main branch push

## Monitoring
- Uptime monitoring (UptimeRobot, StatusCake)
- Error tracking (Sentry, Rollbar)
- Resource usage alerts

## Incident Runbooks
- Rollback deploy on failure
- Monitor logs for errors/abuse
- Contact hosting support if needed

## Backup/Restore
- No persistent user data
- Backup server config and deployment scripts