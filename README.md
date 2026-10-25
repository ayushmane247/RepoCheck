# RepoCheck

RepoCheck inspects a public GitHub repository, detects Python pytest tests,
runs detected tests in a restricted Docker container, and reports what those
checks establish. A passing test run is not a claim of production readiness.

## Current checks

- Validates GitHub repository URLs and reads repository metadata.
- Downloads and extracts source archives with size, path, and file type checks.
- Detects pytest-style Python test files (`test_*.py` and `*_test.py`).
- Runs tests in a prebuilt image with no network, bounded CPU, memory and
  process count, a read-only source mount and root filesystem, a non-root user,
  dropped capabilities, and `no-new-privileges`.
- Analyzes the test outcome and returns evidence-backed findings and actions.
- Reports GitHub Actions workflow files, recognized Python test configuration,
  and dependency manifest presence without executing repository configuration.

## API and runner setup

Requirements: Python 3.12 or newer for the Docker runner image, project
dependencies installed in the API environment, and Docker Desktop with its
Linux container engine running.

Build the runner image from the repository root:

```powershell
docker build -t repocheck-python-runner:dev -f runner-image/Dockerfile runner-image
```

Install API requirements and build the frontend before starting FastAPI:

```powershell
python -m pip install -r requirements.txt
Set-Location frontend
npm ci
npm run build
Set-Location ..
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` for the RepoCheck interface. The interactive API
documentation is at `http://127.0.0.1:8000/docs`.

The frontend is a React, TypeScript, and Vite application styled with Tailwind
CSS. It uses Motion for React and Lucide React. Node.js 20.19 or newer is
required to build it. FastAPI serves the production bundle from `frontend/dist`;
when that bundle is absent, the preserved static frontend remains available as
a fallback until the production bundle is built.

For frontend development, start FastAPI in one terminal, then run:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/` during development. Vite proxies API requests to
FastAPI at `http://127.0.0.1:8000`. Run `npm test` and `npm run build` from the
`frontend` directory to test and build the client. The React interface uses
original layered SVG artwork, shows API-derived statuses and configuration,
and ties finding details to the returned data and runner logs. While a request
is active, it polls server-published validation stages and uses indeterminate
progress; the API does not estimate percentages or test counts.

Send `POST /repositories/validate` with a JSON body such as:

```json
{"url": "https://github.com/ayushmane247/RepoCheck"}
```

The interactive frontend also sends an optional UUID in the
`X-RepoCheck-Run-ID` request header. While validation is active, it polls
`GET /repositories/progress/{run_id}` for the current server-side stage. Direct
API clients can omit the header and keep using the same validation request and
response format.

## Understanding the report

- `validation_status` says whether RepoCheck completed the validation workflow.
- `test_status` describes the pytest result: `passed`, `failed`,
  `collection_failed`, `timed_out`, `runner_error`, `no_tests`, `unsupported`,
  or `incomplete`.
- `readiness_assessment` is `checks_passed`, `needs_attention`, or
  `not_assessed`. `checks_passed` means only that the detected tests passed.
- `findings` contains stable codes, severity, explanation, and (when useful) a
  recommendation.
- `configuration_status` is `checked`, `issues_found`, or `not_checked`; the
  `configuration` object lists discovered files and the exact checks performed.
- `status` remains in the response for compatibility with earlier clients.

Example response for a successful run:

```json
{
  "repository": "owner/repo",
  "default_branch": "main",
  "status": "passed",
  "validation_status": "completed",
  "test_status": "passed",
  "readiness_assessment": "checks_passed",
  "configuration_status": "checked",
  "configuration": {
    "workflows": {
      "present": true,
      "count": 1,
      "files": [".github/workflows/ci.yml"],
      "structural_status": "valid",
      "checks": [{"file": ".github/workflows/ci.yml", "status": "valid", "problems": []}]
    },
    "python_test_configuration": {
      "present": true,
      "files": ["pytest.ini", "pyproject.toml"],
      "validity": {"pytest.ini": "valid", "pyproject.toml": "valid"}
    },
    "dependency_manifests": {
      "present": true,
      "files": ["requirements.txt", "pyproject.toml"],
      "syntax_status": {"requirements.txt": "not_checked", "pyproject.toml": "valid"},
      "dependency_resolution": "not_checked"
    }
  },
  "supported": true,
  "language": "python",
  "framework": "pytest",
  "test_files": ["tests/test_api.py"],
  "test_file_count": 1,
  "exit_code": 0,
  "stdout": "1 passed",
  "stderr": "",
  "duration_seconds": 0.42,
  "message": "Python tests completed successfully.",
  "findings": [
    {
      "code": "TESTS_PASSED",
      "severity": "info",
      "title": "Detected tests passed",
      "message": "All tests collected by the restricted pytest run passed. This does not establish overall production readiness.",
      "recommendation": null
    }
  ]
}
```

## Supported scope and limitations

- Python and pytest-style tests only. Other recognized source languages are
  reported as unsupported; this does not mean their repositories are invalid.
- Workflow inspection recognizes `.yml` and `.yaml` files under
  `.github/workflows/`. PyYAML's pinned `safe_load` parser checks syntax and a
  conservative structure: a mapping with a trigger and non-empty `jobs`; each
  job declares `runs-on` or reusable-workflow `uses`; present `steps` are a
  list whose entries declare `run` or `uses`. This is not a GitHub Actions
  schema validator and does not show that a workflow can run successfully.
- Root `pytest.ini`, `tox.ini`, and `setup.cfg` files are checked for INI
  syntax; `pyproject.toml` is checked for TOML syntax. Missing optional files
  are reported as absent and are not treated as failures.
- `requirements.txt`, `pyproject.toml`, and `package.json` presence is
  reported. TOML and JSON syntax are checked where applicable; requirements
  lines are not parsed, and no manifest is installed or dependency-resolved.
- Configuration findings use `NO_GITHUB_ACTIONS_WORKFLOWS`,
  `INVALID_GITHUB_ACTIONS_WORKFLOW`, and
  `INVALID_REPOSITORY_CONFIGURATION`. One malformed file that serves multiple
  roles produces one finding with its roles listed.
- A repository with no detected or collected tests is never reported as passed.
- The runner image includes RepoCheck's pinned test/runtime libraries. Packages
  requested by a submitted repository are not installed, and repository setup
  scripts and Dockerfiles are not run.
- Workflow and configuration parsing happens in the API using trusted pinned
  dependencies. The YAML parser is needed to check workflow syntax and uses
  its safe loader; repository files are only read as data.
- The runner cannot access the network. Projects that require extra packages
  or network services may fail or time out.
- Findings cover implemented checks only. RepoCheck does not assess code
  quality, vulnerabilities, dependency health, or general production readiness.
- Docker restrictions reduce risk but do not guarantee protection from every
  container escape or resource exhaustion attack. Keep Docker and its host
  environment maintained and isolated appropriately.
- GitHub rate limits, unavailable repositories, archive limits, or upstream
  failures can prevent validation.
