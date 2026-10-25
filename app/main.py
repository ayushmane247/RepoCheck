
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.errors import (
    GitHubRateLimitError,
    GitHubUnavailableError,
    RepositoryNotFoundError,
)
from app.inspector import inspect_repository
from app.validation_service import validate_repository
from app.errors import ArchiveDownloadError, UnsafeArchiveError
from app.progress import publish_stage, read_stage
from uuid import UUID

app = FastAPI(
    title="RepoCheck",
    description="Inspect software repositories and validate their readiness.",
    version="0.1.0",
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_BUILD_DIR = FRONTEND_DIR / "dist"
FRONTEND_ENTRY = FRONTEND_BUILD_DIR / "index.html"
FRONTEND_LEGACY_ENTRY = FRONTEND_DIR / "legacy-index.html"


class InspectRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}



@app.post("/repositories/inspect")
def inspect_endpoint(request: InspectRequest) -> dict:
    try:
        return inspect_repository(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GitHubUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/repositories/validate")
def validate_endpoint(
    request: InspectRequest,
    run_id: UUID | None = Header(default=None, alias="X-RepoCheck-Run-ID"),
) -> dict:
    try:
        progress = (lambda stage: publish_stage(run_id, stage)) if run_id else None
        report = validate_repository(request.url, progress=progress)
        if run_id:
            publish_stage(run_id, "Validation report ready")
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (GitHubUnavailableError, ArchiveDownloadError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except UnsafeArchiveError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/repositories/progress/{run_id}")
def validation_progress(run_id: UUID) -> dict[str, str]:
    stage = read_stage(run_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="No active validation stage was found.")
    return {"stage": stage}


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    entry = FRONTEND_ENTRY if FRONTEND_ENTRY.is_file() else FRONTEND_LEGACY_ENTRY
    return FileResponse(entry)


if FRONTEND_ENTRY.is_file():
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="frontend-build")
else:
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend-static")

