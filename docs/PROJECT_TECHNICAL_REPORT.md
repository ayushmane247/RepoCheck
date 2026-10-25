# RepoCheck — Technical Project Audit and Handover

- **Audit date:** 25 October 2026
- **Repository:** `D:\Projects\16.0 RepoCheck`
- **Audited branch:** `main`
- **Purpose:** Technical handover and implementation audit for a B.Tech CSE project.

## Executive summary

RepoCheck is a FastAPI service with a React, TypeScript, and Vite interface. It accepts a public GitHub repository URL, reads repository metadata, downloads a bounded ZIP archive, safely extracts it, detects Python pytest-style tests, inspects a limited set of configuration and workflow files, and asks a prebuilt Docker image to run pytest against the source. The API then returns a report with separate validation, test, readiness, and configuration statuses and evidence-based findings.

The implemented scope is deliberately narrow. It runs Python/pytest checks only. It does not install dependencies declared by the submitted repository, run its setup scripts or Dockerfile, validate all GitHub Actions semantics, audit vulnerabilities, or establish that a repository is production-ready. A passing run means only that the tests collected by this implementation passed under the configured runner.

### Verification outcome

- Backend suite: **89 passed** using Python 3.13.2, `-p no:cacheprovider`, and a fresh pytest base directory under the ignored `frontend/node_modules/.cache` tree. The initial attempts encountered Windows temp/cache permission errors; the corrected isolated location allowed the complete suite to finish.
- Frontend suite: **11 passed** across 2 test files using the approved npm execution path.
- Frontend production build: **passed** (`tsc --noEmit` and Vite build).
- `git diff --check`: **passed**; Git emitted only LF-to-CRLF working-copy notices for existing changed files.
- Live API: `GET /health` returned 200; `GET /` returned 200; a real, unstubbed `POST /repositories/validate` for `https://github.com/ayushmane247/RepoCheck` returned **HTTP 200**. GitHub metadata was read and the response reported repository `ayushmane247/RepoCheck`, branch `main`, Python/pytest support, and 6 detected test files. The actual test status was **`timed_out`**, readiness **`needs_attention`**, configuration **`checked`**, no exit code, and no runner output. Findings were `TEST_TIMEOUT` (error) and `NO_GITHUB_ACTIONS_WORKFLOWS` (info). This is not a successful test run.
- The audit terminal had Docker CLI 29.2.1 but could not query the Docker Engine named pipe (`permission denied` for `npipe:////./pipe/docker_engine`). The live API did return the runner's timeout outcome, but this audit could not independently inspect Docker daemon/container state. The observed API timing was 32.452 seconds, consistent with the configured 30-second runner timeout plus overhead.
- The React production bundle was served by the running app's root route. No automated real-browser screenshot/visual check was performed. Responsive behavior and reduced-motion handling were reviewed in source/CSS and covered only to the extent of existing component tests.

## 1. Product purpose and implemented scope

### Problem and intended users

RepoCheck gives a repository owner or reviewer a repeatable first-pass signal about whether a public repository has recognizable Python tests, whether those tests can run in a restricted environment, and whether a few declared setup files look structurally sound. The intended users include students, maintainers, reviewers, and teams triaging repositories before investing in a deeper manual review.

The product provides evidence rather than a generalized quality score. Users can inspect the findings, repository facts, configuration checks, runner logs, and recommendations in the frontend. The page differentiates a completed validation workflow from a passing test result and from the narrower readiness assessment.

### Current behavior versus planned extensions

Current source implements one test runner: pytest in a prebuilt Python image. Recognized non-Python source languages can be identified as unsupported, but they are not executed. The service performs limited workflow/configuration parsing and reports manifest presence. It does not resolve dependencies, install repository packages, run other language toolchains, or make claims about application correctness beyond the captured tests.

Natural future work could include additional isolated runner images, richer but schema-backed configuration checks, durable progress for multiple application workers, explicit rate/concurrency limits, and repeatable browser-level visual testing. These are recommendations only; no such features are claimed as implemented by this audit.

### Automated testing compared with manual inspection

Automated tests are repeatable and can exercise URL validation, archive attack cases, detection rules, status mapping, configuration parsing, API behavior, and frontend interactions. They cannot establish that every possible repository is safe, that the production Docker host is configured securely, or that a GitHub workflow will run successfully. Manual inspection remains necessary for assumptions outside the implemented checks, deployment configuration, and results that need broader context. Conversely, a manual glance is not a substitute for repeatable tests of path traversal, malformed archives, or edge-case status mapping.

## 2. Repository layout

The following tree lists meaningful source and test files. Generated environments and build output are summarized afterward.

```text
.
├── README.md                         # Setup, API, limitations, and report semantics
├── requirements.txt                  # Pinned Python API/test dependencies
├── .gitignore                        # Ignores virtualenv, caches, build output, env files
├── app/
│   ├── main.py                       # FastAPI routes and frontend serving
│   ├── errors.py                     # Domain/upstream exception types
│   ├── github_urls.py                # GitHub URL validation
│   ├── github_client.py              # Read-only GitHub REST client
│   ├── inspector.py                  # Metadata, recursive tree, manifest summary
│   ├── source_archive.py             # Archive download and safe ZIP extraction
│   ├── detector.py                   # Python test and language detection
│   ├── configuration.py              # Workflow, pytest config, manifest checks
│   ├── runner.py                     # Restricted Docker invocation
│   ├── analysis.py                   # Status derivation and finding generation
│   ├── validation_service.py         # End-to-end orchestration and cleanup
│   └── progress.py                   # In-process coarse progress registry
├── runner-image/
│   └── Dockerfile                    # Prebuilt pytest runtime image
├── fixtures/sample-python/
│   ├── Dockerfile                    # Trusted fixture-runner image recipe
│   └── test_math.py                  # Small controlled runner fixture
├── frontend/
│   ├── package.json / package-lock.json
│   ├── index.html                    # Vite entry document
│   ├── legacy-index.html             # Static fallback when dist is absent
│   ├── vite.config.ts                # React/Tailwind plugins, dev proxy, Vitest
│   ├── src/
│   │   ├── main.tsx                  # React root and active stylesheet
│   │   ├── App.tsx                   # Intro, briefing, analysis, and report scenes
│   │   ├── types.ts                  # API report and UI types
│   │   ├── feedback.ts               # Finding evidence/recommendation enrichment
│   │   ├── services/api.ts           # Validate request and progress polling calls
│   │   ├── styles.css                # Active responsive and motion styles
│   │   ├── components/RooftopArtwork.tsx
│   │   ├── components/WebSlingerScene.tsx
│   │   ├── App.test.tsx
│   │   ├── feedback.test.ts
│   │   └── test/setup.ts
│   ├── app.js / feedback.js / styles.css
│   │                                  # Preserved legacy frontend fallback assets
│   └── public/                       # Older SVG assets; React uses inline SVG artwork
└── tests/
    ├── test_analysis.py
    ├── test_archive_download.py
    ├── test_configuration.py
    ├── test_detector.py
    ├── test_frontend.py
    ├── test_github_client.py
    ├── test_github_urls.py
    ├── test_health.py
    ├── test_inspector.py
    ├── test_progress.py
    ├── test_runner.py
    ├── test_source_archive.py
    ├── test_validation_service.py
    └── frontend_feedback.test.cjs
```

Generated or ignored material includes `.venv/`, Python bytecode, `.pytest_cache/`, `frontend/node_modules/`, `frontend/dist/`, test temporary directories under the ignored dependency tree, and coverage/build output. It should not be committed as application source. There is no Jenkinsfile or deployment manifest in the audited tree.

## 3. Backend design

### `app/main.py`: HTTP boundary

The FastAPI application is titled RepoCheck, version `0.1.0`.

| Route | Behavior | HTTP-level failures |
|---|---|---|
| `GET /health` | Returns `{"status":"ok"}`. This is a shallow process health check. | Normally 200 while the application serves requests. It does not check GitHub or Docker. |
| `POST /repositories/inspect` | Reads GitHub metadata and recursive tree, then reports recognized dependency manifest paths. | 400 invalid URL/input, 404 repository/resource missing, 429 GitHub rate limit, 502 GitHub upstream failure, 422 request validation. |
| `POST /repositories/validate` | Runs the validation workflow and returns a report object. | 400 invalid URL, 404 missing repository, 429 rate limit, 502 GitHub/archive upstream error, 422 unsafe archive, 422 malformed request. |
| `GET /repositories/progress/{run_id}` | Returns a coarse server-published stage for a UUID while it is present in the process registry. | 404 unknown/expired ID; malformed UUID is rejected by FastAPI validation (422). |
| `GET /docs`, `GET /openapi.json` | FastAPI-generated interactive docs and OpenAPI document. | Standard FastAPI behavior. |
| `GET /` and static paths | Serves `frontend/dist` when built; otherwise returns the preserved `frontend/legacy-index.html` and its `/static` assets. | Static serving errors if the expected entry/assets are missing. |

`InspectRequest.url` is a required string with a 1–2048 character constraint. There is no declared Pydantic response model for the two repository routes: clients receive dictionaries, and the validate report schema is therefore enforced by implementation/tests rather than a strict response model. A request body that fails model validation receives HTTP 422. A valid request that discovers failing tests or a timeout still normally receives HTTP 200; callers must inspect the returned business-status fields.

The optional `X-RepoCheck-Run-ID` header is parsed as UUID. If provided, the validate route publishes progress; omission preserves compatibility with clients that only send `{"url":"..."}`. The progress registry is process-local, lock-protected, and expires entries after ten minutes. It is not durable and is not shared across multiple Uvicorn workers or hosts.

### Domain modules and call flow

1. `github_urls.parse_github_url` requires HTTPS, host `github.com`, no credentials or custom port, no query/fragment, and exactly an owner/repository path. It rejects traversal-like segments, backslashes, NULs, and encoded separators.
2. `github_client.GitHubClient` performs read-only, unauthenticated GitHub API requests with a 10-second timeout, a fixed API version and User-Agent, redirects disabled, and explicit handling for missing resources, rate limits, timeouts, transport failures, and invalid responses.
3. `inspector.inspect_repository` obtains the repository's default branch, metadata, recursive Git tree, and paths whose basename is `requirements.txt`, `pyproject.toml`, or `package.json`. GitHub's truncated tree is rejected rather than silently treated as complete.
4. `source_archive.download_archive` retrieves the default-branch ZIP through GitHub's archive endpoint. It allows HTTPS only for `api.github.com` and `codeload.github.com`, validates every redirect, caps redirects/attempts, applies a 20-second HTTP timeout, and enforces a 25 MiB streamed archive limit.
5. `source_archive.extract_archive_safely` validates and extracts ZIP entries beneath a fresh temporary workspace. It requires one archive root and an empty destination, rejects unsafe paths, traversal, absolute/drive-like paths, Windows reserved names/streams, links and special files, duplicate/case-colliding paths, file/directory collisions, suspicious compression ratios, more than 2,000 entries, or more than 100 MiB expanded content. It writes files exclusively and cleans partial extraction on failure. It does not run extracted code.
6. `configuration.inspect_configuration` reads recognized files as data. It examines YAML under `.github/workflows/`, root pytest configuration (`pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`), and root manifests (`requirements.txt`, `pyproject.toml`, `package.json`). Config reads are capped at 1 MiB. It uses safe YAML loading, Python TOML parsing, JSON parsing, and INI syntax parsing. It does not interpret a full GitHub Actions schema or resolve dependencies.
7. `detector.detect_support` identifies Python test paths ending in `test_*.py` or `*_test.py`; it ignores common generated/vendor directories. Python tests select pytest. If no Python files are present, known extensions can identify languages such as JavaScript/TypeScript, Java, Go, Rust, Ruby, PHP, C#, C/C++, Swift, and Kotlin as unsupported. Detection is based on paths, not a semantic project-language analysis.
8. `runner.DockerRunner.run_source` runs the discovered source in the fixed, prebuilt image. It makes no call to pip/npm for repository dependencies. The runner's default image command invokes pytest over `/workspace`.
9. `analysis.analyze_readiness` maps the runner and configuration results to statuses and findings. `validation_service.validate_repository` coordinates these steps, makes conservative reports for unsupported inputs or internal failures, and removes the temporary workspace in a `finally` block.

`app/errors.py` contains typed errors that keep URL, GitHub, archive transport, and unsafe-archive failures distinct at the HTTP boundary. Unknown exceptions inside the validation workflow are represented as an incomplete/error report rather than being mistaken for a passed test result.

### Status model and edge cases

The status fields answer different questions:

- `validation_status`: whether RepoCheck completed its workflow (`completed` versus `failed`/incomplete path).
- `test_status`: the runner/test outcome: `passed`, `failed`, `collection_failed`, `timed_out`, `runner_error`, `no_tests`, `unsupported`, or `incomplete`.
- `readiness_assessment`: `checks_passed`, `needs_attention`, or `not_assessed`. `checks_passed` requires a passing supported test run and no configuration issues detected by the implemented checks. This is not general production readiness.
- `configuration_status`: `checked`, `issues_found`, or `not_checked`.
- `status`: retained for compatibility with the earlier response format; new clients should use the more specific fields above.
- `findings`: stable codes, severity, title/message, and recommendation, with optional file/role context. Informational absence of workflows is not a failed test result.

In particular, pytest exit 5 is treated as no tests collected, collection errors do not become success, timeout has no asserted exit code, Docker invocation errors remain runner errors, unsupported languages are not executed, and no supported files do not become a pass. HTTP 200 describes successful handling of the request, not successful tests.

## 4. Docker execution and security review

### Runner image and invocation

`runner-image/Dockerfile` uses `python:3.12-slim`, installs pinned pytest 8.4.2 and the runtime libraries already listed in the image, disables pytest plugin autoload and bytecode writes, sets `HOME=/tmp`, uses `/workspace`, and switches to UID/GID `10001:10001`. Build it from the repository root:

```powershell
docker build -t repocheck-python-runner:dev -f runner-image/Dockerfile runner-image
```

`run_source` uses an argument array with `shell=False`, a unique container name, a fixed image and no user-supplied command. The actual `docker run` restrictions are:

- `--network none`
- `--memory 128m`, `--cpus 0.5`, and `--pids-limit 64`
- `--read-only` root filesystem
- writable `/tmp` tmpfs limited to 16 MiB with `noexec,nosuid`
- `--cap-drop ALL`, `--security-opt no-new-privileges`
- non-root `--user 10001:10001`
- source bind-mounted at `/workspace` read-only
- `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and `HOME=/tmp`
- 30-second run timeout; on timeout it tries `docker kill`, then always attempts `docker rm -f` with bounded cleanup calls
- captured stdout and stderr each truncated to their last 10,000 characters

The image's libraries are RepoCheck's runner prerequisites; they are not selected from the repository manifest. Repository dependencies and install/build commands are not run. The separate `run_fixture` method builds/runs a trusted sample fixture and is not the source-validation API path.

### Security strengths and assumptions

The code avoids shell interpolation and arbitrary command input, keeps the source mount read-only, disables network access in the runner, caps CPU/memory/processes/runtime/output, drops capabilities, runs non-root, and does not execute archive-provided setup instructions. Archive path and size controls reduce extraction attacks. GitHub URL and archive redirect allowlists reduce SSRF exposure. Configuration parsing uses bounded reads and safe YAML parsing.

These controls reduce risk; they do not prove hostile repository tests cannot exploit the Linux kernel, Docker, pytest, or an image dependency. The Docker daemon is a sensitive host capability. The service relies on the daemon's isolation and the operator's host configuration. The code does not specify a custom seccomp profile, AppArmor/SELinux policy, user namespace, or a microVM boundary. The read-only source and root filesystem still leave the bounded `/tmp` tmpfs writable. Docker image packages are fetched during image build, so the build supply chain and pinned version lifecycle remain operational concerns.

The API currently shows no authentication, per-user quota, global concurrency cap, or rate limiting. Multiple simultaneous validations can consume temporary storage, API bandwidth, and daemon capacity even with per-container limits. A production host should isolate the daemon and worker from important host data, keep images and Docker updated, limit API exposure, and monitor job concurrency and cleanup. Treat these as deployment prerequisites, not as controls already supplied by the application.

## 5. Frontend architecture and UX

### Stack and components

The active application is React 19 with TypeScript 7 and Vite 8. Tailwind CSS 4 is integrated through the Vite plugin; Motion for React handles scene and finding transitions; Lucide React supplies interface icons. `main.tsx` mounts `App` under React Strict Mode and imports `src/styles.css`.

`App.tsx` owns the intro, repository briefing, active analysis, error, and report states. `RooftopArtwork.tsx` composes the inline SVG scene from `WebSlingerScene.tsx`. `services/api.ts` calls the same-origin API and validates/converts HTTP/network failures into frontend errors. `types.ts` gives the UI a typed model for findings, configurations, and reports. `feedback.ts` adds explanations based on actual finding codes and captured runner output; it does not invent backend statuses or test results.

### User interactions and truthfulness

The form accepts HTTPS GitHub URLs and prevents duplicate submissions while a request is pending. A UUID run ID lets the client poll `/repositories/progress/{run_id}` for coarse server-published activity; the loading screen uses an indeterminate bar and does not show fabricated percentages. The server activity is stage-level, not individual test progress, and can be absent for older/direct clients. Retry and new-analysis actions are provided. The RepoCheck wordmark in the active React interface explicitly cancels/clears the current analysis state and navigates to the intro scene, rather than relying only on `#top` scrolling.

When a response arrives, the report state is derived from the API statuses and finding severity. Findings can be filtered by severity and expanded for evidence, impact, recommendation, and confidence/limitation. The field snapshot presents repository metadata and checked configuration. Native `<details>` exposes the terminal record; copy actions provide status feedback. React renders report/log strings as text. Error/network states say that no conclusive repository judgment was returned and provide retry/edit actions.

Animations use Motion and CSS/SVG, with `useReducedMotion` and reduced-motion CSS handling. The active stylesheet includes responsive breakpoints (900, 700, 420, 380 px), focus styling, and mobile-oriented layout adjustments. Semantic headings, labels, buttons, `aria-expanded`, status/alert roles, and keyboard-operable native controls are present. The current result layout places Findings and Field snapshot as sibling columns at wide widths and stacks them at narrow widths.

### Legacy assets and verification limits

`frontend/app.js`, `feedback.js`, root `styles.css`, and `legacy-index.html` are retained as a fallback when no Vite production bundle exists. The active React app imports `frontend/src/styles.css`; the legacy styles are not its primary stylesheet. The older SVGs under `frontend/public/` are not the component artwork currently rendered by React; Vite may still copy public assets into the bundle. Keeping both paths means future maintenance should distinguish active React code from fallback code.

Vitest/Testing Library verifies component and feedback behavior, but this audit did not use Playwright or another real browser automation tool. The successful Vite production build and HTTP root response establish build/serving behavior, not pixel-level visual correctness on every viewport or screen reader. Manual responsive and reduced-motion review was source-based.

## 6. API contract and report fields

### Request examples

```http
POST /repositories/validate
Content-Type: application/json
X-RepoCheck-Run-ID: <optional UUID>

{"url":"https://github.com/owner/repo"}
```

`POST /repositories/inspect` uses the same JSON request shape. The validation response is a JSON object with fields that may be absent or null depending on how far validation got:

| Field | Meaning |
|---|---|
| `repository`, `default_branch` | GitHub's canonical full name and default branch, when available. |
| `status`, `validation_status`, `test_status` | Compatibility status plus workflow and runner outcome. |
| `readiness_assessment`, `configuration_status`, `configuration` | Narrow readiness result and structured configuration summary. |
| `supported`, `language`, `framework` | Detector result; currently pytest is the only supported execution framework. |
| `test_files`, `test_file_count` | Relative paths and count matching implemented detection rules. |
| `exit_code`, `stdout`, `stderr`, `duration_seconds` | Captured restricted-run result; timeout/runner error may have null exit code and empty output. |
| `message` | Human-readable summary for the outcome. |
| `findings` | Evidence-backed, coded result findings. |

The validation endpoint can return HTTP 200 with a failed test, a timeout, unsupported language, or an incomplete report. Error-level HTTP codes are reserved for request or upstream/archive handling. The frontend must inspect statuses rather than infer success from HTTP 200. Progress GET returns `{"stage":"..."}`; it is not a percent or test counter.

## 7. Dependencies and local setup

### Declared versions

The Python `requirements.txt` pins FastAPI 0.121.3, Uvicorn 0.38.0, httpx 0.28.1, pytest 8.4.2, and PyYAML 6.0.2. The container image pins pytest 8.4.2, FastAPI 0.121.3, httpx 0.28.1, and PyYAML 6.0.2. Frontend direct dependencies are React/React DOM 19.3.1, Motion 14.6.0, and Lucide React 1.61.0. Dev dependencies include Vite 8.3.5, TypeScript 7.0.2, Tailwind 4.3.3, Vitest 4.1.12, React Testing Library 16.3.3, and jsdom 29.1.1. The lockfile should be used with `npm ci` for repeatable installs.

At audit runtime, the host Python was 3.13.2 with FastAPI 0.115.12 and pytest 8.3.5 installed; this differs from `requirements.txt`. httpx 0.28.1 and PyYAML 6.0.2 matched. The container is explicitly Python 3.12. This environment mismatch is a reproducibility risk; CI should create a clean environment from declared requirements before relying on host results.

Node was v20.19.4 and npm 11.6.0 on the approved execution path. `npm.cmd` resolves to `C:\nvm4w\nodejs\npm.cmd`, a shim/symlink path that requires traversing the protected `C:\Users\Aniket` profile. Normal sandbox execution failed with `EPERM` while Node called `lstat` on that profile path; the project itself was not the cause. Tests and build completed using the approved elevated execution path. No system-wide settings or permissions were changed.

### Development setup

Requirements: Python 3.12 or newer, Node 20.19 or newer, and Docker Desktop running a Linux container engine. From the repository root:

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
docker build -t repocheck-python-runner:dev -f runner-image/Dockerfile runner-image
Set-Location frontend
npm ci
npm run build
Set-Location ..
uvicorn app.main:app --reload
```

The interface is available at `http://127.0.0.1:8000/`, API docs at `/docs`, and health at `/health`. For frontend development, keep FastAPI running, then use another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Vite serves `127.0.0.1:5173` and proxies `/repositories`, `/health`, `/docs`, and `/openapi.json` to port 8000. Production FastAPI serves `frontend/dist` at the same origin, avoiding the need for browser CORS configuration in the default deployment. When the dist directory is absent, the legacy static frontend is served as a fallback.

No application environment variables were identified in the reviewed source/README. There is no GitHub token setting; calls are unauthenticated and subject to public API rate limits. There is no `.env.example` in the listed project tree.

## 8. Test and verification record

| Check | Result | Interpretation |
|---|---|---|
| Backend `python -m pytest -q -p no:cacheprovider --basetemp <fresh ignored path>` | 89 passed in 48.77 s | Unit and controlled-fixture coverage passed on the available host Python. This does not mean the live repository run passed. |
| Frontend `npm.cmd test -- --reporter=dot` | 2 files, 11 tests passed | Component/API-feedback behavior passed under Vitest/jsdom. |
| Frontend `npm.cmd run build` | Passed; 2,355 modules transformed | TypeScript check and Vite production bundle completed. |
| `git diff --check` | Passed | No whitespace errors in tracked diffs; line-ending notices were informational. |
| `GET /health` | HTTP 200 | Process answered the health request. |
| `GET /` | HTTP 200, HTML | Production entrypoint was served. |
| Live `POST /repositories/validate` | HTTP 200; actual report says `timed_out` | Real GitHub inspection/archive flow reached a timeout report for tests; not a pass. Six test files were detected. |
| Direct Docker Engine CLI check from audit terminal | Permission denied on Docker named pipe | No independent container inspection was possible from this terminal. |
| Browser-level visual test | Not run | No browser automation was used; do not interpret source review as screenshot verification. |

The tests exercise controlled edge cases including no supported files, failures, pytest collection failures, timeout/runner errors, and unsupported language mapping. These are unit/fixture-level scenarios, not a live Docker adversarial test. The live API result itself is evidence that a timed-out run is not represented as successful: it returned `test_status=timed_out`, `readiness_assessment=needs_attention`, null exit code, and a `TEST_TIMEOUT` error finding.

## 9. Proposed Jenkins pipeline (design only)

No Jenkinsfile was created. A safe initial pipeline should separate fast deterministic checks from environment-dependent integration checks:

1. **Checkout and inventory** — use a disposable Linux agent; record commit SHA and tool versions; do not run with a privileged shared host identity.
2. **Python environment** — create a fresh virtual environment and install only the repository's pinned API/test requirements. Run the backend pytest suite and publish JUnit XML. Include the pinned/declared dependency environment in the report.
3. **Frontend** — run `npm ci`, `npm test -- --reporter=dot`, and `npm run build`; archive the generated frontend bundle only if that is a release artifact.
4. **Runner image build** — build `repocheck-python-runner:dev` from `runner-image/Dockerfile`. This requires a Docker-capable agent and outbound package/image registry access during build. Do not make the Jenkins agent itself a container with an unnecessarily exposed host Docker socket.
5. **Controlled Docker runner checks** — run the existing fixture tests on a disposable worker with the required Linux Docker engine; verify the no-network, read-only mount, limits, non-root user, and cleanup behavior. Keep test output and container/image identifiers for diagnosis.
6. **Optional public GitHub integration** — run separately and label it non-deterministic. It requires outbound GitHub/API/archive access, is subject to unauthenticated rate limits, and may time out if the target's tests exceed the configured limit. Do not make a moving public repository the only release gate; use a pinned fixture or controlled test repository for stable end-to-end checks.
7. **Publish results** — archive JUnit, frontend build output as appropriate, and sanitized logs. Do not publish secrets or unrestricted repository output as public artifacts.

Prerequisites include a disposable Linux agent, Python and Node versions aligned to project requirements, network access for dependency/image downloads, a Docker daemon isolated for this job, disk cleanup, timeout policy, and Jenkins plugins for JUnit/artifacts if those publishers are selected. Build-stage dependency downloads should be pinned and reviewed. A deployment credential is not currently needed for public GitHub reads and should not be introduced unless an explicit authenticated feature is designed.

## 10. Deployment and operations assessment

### Sensible deployment shape

The simplest current shape is a single-origin FastAPI service that serves the built React bundle and calls a Docker runner on a dedicated Linux host. This matches the relative API URLs and avoids separate-origin CORS configuration. The service still requires Docker CLI access and an isolated daemon capable of running the prebuilt image. A generic serverless web host without access to a suitable isolated container runtime is not a fit for the current execution design.

Do not expose a general-purpose production Docker socket to an internet-facing API process on a valuable host. Prefer a dedicated worker/VM or a carefully isolated runner service, with network policy separating the public web/API tier from the Docker execution host. If the threat model requires stronger isolation for hostile test code, assess microVM or sandboxed-runtime options before accepting public submissions. This is an architectural deployment decision; no platform choice is implemented in this repository.

### Operational controls to add or configure

- Terminate TLS and enforce request/body limits at a reverse proxy. The source URL body is small, but archive data and repository names are externally supplied.
- Set proxy/request timeouts longer than the maximum end-to-end operation. GitHub API calls can take up to 10 seconds each, archive download up to 20 seconds, and Docker execution 30 seconds plus cleanup; a single short proxy timeout can terminate valid reports.
- Add a global queue/concurrency limit and bounded worker capacity. Per-container limits alone do not cap aggregate resource use.
- Monitor Docker daemon health, image availability, disk usage, temp cleanup, upstream failures, timeout rate, and GitHub rate limits. Current `/health` checks only that FastAPI responds.
- Avoid logging full raw output by default if it may contain repository-controlled strings or secrets. Define log/artifact retention and access policies.
- The in-memory progress registry works in a single process. Multiple workers or replicas need sticky routing or a shared expiring store; a shared store is more reliable. Otherwise a progress GET can hit a worker that did not process the POST.
- CORS is not configured because the default React and API deployment is same-origin. A separate frontend origin would require an explicit API base URL and narrowly scoped CORS/proxy configuration; neither should be assumed to work today.
- Add authentication or rate limiting if access should not be open to anonymous arbitrary submissions. Public GitHub API limits currently apply to unauthenticated calls.
- Keep runner image and host updates controlled and tested. The current report is evidence for a particular execution, not a long-term guarantee about upstream dependencies or host state.

## 11. Git state, known limitations, and next steps

### Working tree state observed before this report

The tree was already non-clean on branch `main`: 7 tracked files had modifications (`.gitignore`, `README.md`, `app/errors.py`, `app/main.py`, `app/runner.py`, `requirements.txt`, `tests/test_runner.py`) and there were 17 untracked implementation/test paths (`app/analysis.py`, `app/configuration.py`, `app/detector.py`, `app/progress.py`, `app/source_archive.py`, `app/validation_service.py`, `frontend/`, `runner-image/`, and the new analysis/archive/configuration/detector/progress/source-archive/validation-service/frontend tests). Those changes predate this report and have not been staged, committed, or discarded. This audit adds only `docs/PROJECT_TECHNICAL_REPORT.md`.

### Known limitations and technical debt

- Only pytest is executed; other languages are informationally unsupported.
- The live target timed out under the configured run and could not be independently inspected at the Docker daemon because the current audit terminal was denied named-pipe access.
- Dependencies declared by a repository are not installed or resolved. Repositories that need extra packages or services may fail for environmental reasons.
- GitHub Actions checks are conservative structural checks, not GitHub's full workflow/schema validation or an execution result.
- The progress store is in memory, process-local, and coarse; it has no durable job queue or cancellation API for an already-started Docker invocation beyond request/process behavior.
- API responses have no strict declared response model, and HTTP 200 contains business-level failure outcomes.
- No authentication, request quotas, aggregate concurrency control, metrics, or persistent audit store are present in the reviewed application.
- `requirements.txt` in the host audit environment did not match installed FastAPI/pytest versions; clean CI environments are needed for reproducibility.
- Frontend tests/build are automated, but no real-browser visual/responsive or assistive-technology test was run.
- The legacy static frontend and old public SVGs remain alongside the active React source, so maintainers need to avoid editing the wrong implementation path.
- Container isolation is not a guarantee against host/kernel escape. Docker host configuration and service exposure remain deployment risks.

### Suggested handover sequence

1. Build the runner image and run the controlled fixture with Docker access available; document the engine/runtime versions.
2. Run the live target again from an environment with Docker access and capture returned `test_files`, runner output, timeout, and progress-stage observations. Keep the timeout result if reproducible; do not describe it as passing.
3. Standardize Python/Node versions in CI to the declared files and publish backend/frontend test artifacts.
4. Choose an isolated job execution topology, then add aggregate queue/concurrency controls, request limits, and multi-worker progress storage before opening the service to public traffic.
5. Add browser-level checks for desktop/mobile breakpoints, reduced motion, keyboard flow, copy feedback, and report states if visual regression confidence is required.
6. Decide whether to remove or deliberately maintain the fallback frontend in a separate future change after confirming deployment needs.

## Glossary

- **Archive extraction:** turning the downloaded repository ZIP into files inside a temporary directory after validating its paths and resource limits.
- **Docker runner:** the prebuilt container that executes pytest against the read-only extracted repository source.
- **Finding:** a coded, severity-labelled statement tied to an implemented check and its evidence.
- **Readiness assessment:** RepoCheck's narrow aggregate interpretation of supported test and configuration outcomes; not a security or production certification.
- **Runner timeout:** the configured time limit ended execution before a result could be established; this is not a pass or a normal test failure.
- **Unsupported repository:** a repository for which the current implementation does not have a supported test runner; it is not necessarily invalid or broken.
