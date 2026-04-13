# CI/CD Enhancement

## Pipeline Security
- Pin all GitHub Actions to commit SHA
- Use OIDC for deployment secrets
- Scan dependencies for vulnerabilities
- Require code review for all PRs

## Example GitHub Actions Workflow
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Lint
        run: flake8 backend/
      - name: Test
        run: pytest backend/
      - name: Build frontend
        run: |
          cd backend/static/css
          npx tailwindcss -i input.css -o tailwind.min.css --minify
      - name: Deploy
        uses: vercel/action@v2
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
```

## Supply Chain Security
- Dependabot for dependency updates
- Snyk or similar for vulnerability scanning