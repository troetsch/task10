# DevOps Basics - Deployments - Carlos - Task 10 - Docker Build Fixes Notes

> Snapshot: 23-10-2025

Review of issues found and fixes applied, additionally some extra notes for better understanding and future reference.




How to run & test the app locally 
- Build the image (use the task folder as the build context):
  ```
  docker build -t flask-app:local path/to/repo
  ```
- Run the container (maps the app's port 8000):
  ```
  docker run --rm -p 8000:8000 --name flask-local flask-app:local
  ```
- Quick health checks:
  ```
  curl -v http://localhost:8000/health
  curl -v http://localhost:8000/
  ```
- Create a task (POST):
  ```
  curl -s -X POST http://localhost:8000/api/tasks \
    -H "Content-Type: application/json" \
    -d '{"title":"my task"}' | jq
  ```
- Run the unit tests inside the image:
  ```
  docker run --rm flask-app:local python -m unittest /app/test_app.py -v
  ```
- Run the app locally without Docker (dev flow):
  ```
  cd path/to/repo
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python app.py
  # then curl the health endpoint as above
  ```

What was wrong (docker-build part) — step-by-step diagnosis and fixes
1) Problem: requirements.txt was not a plain pip file
   - Symptom: `ModuleNotFoundError: No module named 'flask'` at container runtime.
   - Root cause: requirements.txt was corrupted, so pip couldn't parse/install Flask during image build.
   - Fix applied: replaced requirements.txt with plain text once again:
     ```
     Flask==3.0.0
     Werkzeug==3.0.1
     ```

2) Problem: packages installed with `pip --user` and then copied from `/root/.local`
   - Symptom: installed packages were not usable by the non-root runtime user; subsequent COPY of `/root/.local` failed or was missing.
   - Root cause(s):
     - `pip install --user -r requirements.txt` installs to `/root/.local` inside the builder stage. That requires copying `/root/.local` into the runtime image and PATH set to `/root/.local/bin`. If not done correctly, runtime Python can't find the packages.
     - The Dockerfile attempted to COPY `/root/.local` from the builder but the directory wasn't present (or not created) at the point of copy — build failed with `"/root/.local": not found` or packages not visible.
   - Fix applied:
     - Simplified to a single-stage Dockerfile that installs packages system-wide (no `--user`) so packages are available in the runtime Python path, and/or in multi-stage builds used `/usr/local`.
     - Explicitly ran `pip install --no-cache-dir -r /app/requirements.txt` in the image so flask is available.

3) Problem: malformed / duplicated Dockerfile content and stray Markdown fences
   - Symptom: Docker build warnings and duplicate-stage errors, confusing build behavior and causing unexpected layers to be created or to reference missing stages.
   - Root cause: the Dockerfile had leftover markdown fences and duplicated multi-stage sections, sometimes with both `as builder` and `AS builder` repeats; also stray trailing lines (e.g. duplicated RUNs). This produced warnings and build failures.
   - Fix applied:
     - Replaced the broken Dockerfile with a clean, readable Dockerfile (single-stage for reliability in this exercise). Key parts:
       - WORKDIR /app
       - COPY requirements.txt and install (system)
       - COPY app.py and test_app.py into `/app/`
       - Create non-root user and chown /app
       - CMD ["python", "app.py"]

4) Problem: COPY semantics / build context mismatch (files missing from final image)
   - Symptom: At runtime /app did not exist or `app.py` not found in the image (python couldn't open `/app.py` or files were missing).
   - Root causes:
     - The Dockerfile used relative COPY but Docker build context was not the task directory.
     - The CI docker build command used `.` as the context (root of repo), which can lead to different paths or to accidentally not including files if .dockerignore excludes them.
   - Fix applied:
     - In the Dockerfile use explicit destination paths (e.g. `COPY app.py /app/app.py`) to be explicit.
     - In CI changed build command to set the correct context: `docker build -t flask-app:${{ github.sha }} path/to/repo` so Docker’s context contains the expected files.
     - Added an empty `.dockerignore` where needed to be explicit (so Docker doesn't send a tiny unrelated context).

5) Problem: mismatched ports in health checks (CI vs app)
   - Symptom: CI health check failed even though container may have started (because health check was hitting a different port).
   - Root cause: the health check in CI used a different port than the app was serving, or port mapping didn't match the app's internal port.
   - Fix applied:
     - Ensured Dockerfile/app serve on port 8000 and CI uses `-p 8000:8000` and `curl http://localhost:8000/health`. (If you prefer port 5000, adjust both the app and CI to match.)

6) Problem: test-run inside container used an incorrect path to tests
   - Symptom: `docker run --rm flask-app:latest python -m unittest test_app.py` would fail because test file not at container CWD or path.
   - Fix applied:
     - Make test invocation use the absolute path inside image `/app/test_app.py` (or ensure WORKDIR=/app and `COPY` places files there). Example: `docker run --rm flask-app:latest python -m unittest /app/test_app.py -v`

7) Problem: CI used `docker save` without preserving artifacts in workspace
   - Minor issue: artifact path and upload needed to be consistent with `$GITHUB_WORKSPACE`
   - Fix applied:
     - Save to `$GITHUB_WORKSPACE/artifacts/flask-app.tar.gz` and upload via `actions/upload-artifact@v4` so the artifact is available.
8) Problem: trivy scan upload step to codeql wasn't done properly - requires additional API permissions
   - Minor issue: the workflow didn't have `security-events: write` permission to upload SARIF results.
   - Fix applied:
     - Added `security-events: write` to the workflow permissions (only for example purpose)
     - Upload SARIF artifact using `actions/upload-artifact@v4` so results are preserved, without needing `codeql` upload setup and settings.

Summary checklist (what to verify locally after these fixes)
- Verify the fixed requirements.txt:
  ```
  cat requirements.txt
  ```
- Build from the task folder:
  ```
  docker build -t flask-app:local path/to/repo
  ```
- Run and curl health:
  ```
  docker run --rm -p 8000:8000 --name t flask-app:local
  curl http://localhost:8000/health
  ```
- Run tests inside container:
  ```
  docker run --rm flask-app:local python -m unittest /app/test_app.py -v
  ```
- In CI ensure the docker-build step uses:
  ```
  docker build -t flask-app:${{ github.sha }} path/to/repo
  ```
  and health checks use `http://localhost:8000/health`.

Recommendations to avoid recurrence
- Keep `requirements.txt` as plain pip format (no fences).
- Make Dockerfile explicit and minimal:
  - Install packages in the image (or ensure correct multi-stage copying from `/usr/local`).
  - Use explicit `COPY <src> /app/<dest>` so files' destinations are obvious.
  - Set WORKDIR and use absolute paths in CI test/run commands to avoid surprises.
- Always pass the correct build context to `docker build` from CI (point to the folder with Dockerfile and sources).
- Add a Dockerfile healthcheck (COMMENTED but present) so orchestrators/CI can rely on built-in container health.
- Use higher ports (8000+) to avoid conflicts with common services.
- In CI prefer `docker run -d -p 8000:8000` and then `curl -f http://localhost:8000/health`.
- When using a multi-stage builder, verify you copy the same path that pip installs to (system installs go into `/usr/local`); prefer system installs unless you need `--user` for a reason.


Little extra modification for app.py - change port usage from `5000` to `8000` to avoid conflicts, locally unable to run on port `5000`:

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

Dockerfile after fixes (single-stage for simplicity), we already are using `python:3.11-slim` as `base image`, so no need to expand this further - no real benefit from multi-stage here for this simple app:

```Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application files
COPY app.py /app/app.py
COPY test_app.py /app/test_app.py

# Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "app.py"]
```


Finally, here is the corrected docker-build part of Workflow for reference:

```yaml
name: Build Stage - Task 10

permissions:
  contents: read
  security-events: write

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  docker-build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    # needs: test

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build Docker image
      run: |
        docker build -t flask-app:${{ github.sha }} .
        docker tag flask-app:${{ github.sha }} flask-app:latest

    - name: Test Docker image build
      run: |
        docker images flask-app

    - name: Run container health check
      run: |
        docker run -d -p 8000:8000 --name test-container flask-app:latest
        sleep 10
        curl -f http://localhost:8000/health || exit 1
        curl -f http://localhost:8000/ || exit 1
        docker logs test-container
        docker stop test-container
        docker rm test-container

    - name: Run tests inside Docker container
      run: |
        docker run --rm flask-app:latest python -m unittest /app/test_app.py -v

    - name: Save Docker image
      run: |
        mkdir -p "$GITHUB_WORKSPACE/artifacts"
        docker save flask-app:latest | gzip > "$GITHUB_WORKSPACE/artifacts/flask-app.tar.gz"

    - name: Upload Docker image artifact
      uses: actions/upload-artifact@v4
      with:
        name: docker-image
        path: artifacts/flask-app.tar.gz
        retention-days: 7

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: docker-build

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Build Docker image
      run: docker build -t flask-app:scan .

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'flask-app:scan'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Trivy SARIF as artifact
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: trivy-results
        path: trivy-results.sarif
        retention-days: 7
```


### All good, try it yourself.

# `Have fun Carlos! :)`