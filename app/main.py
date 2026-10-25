
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.errors import (
    GitHubRateLimitError,
    GitHubUnavailableError,
    RepositoryNotFoundError,
)
from app.inspector import inspect_repository

app = FastAPI(
    title="RepoCheck",
    description="Inspect software repositories and validate their readiness.",
    version="0.1.0",
)


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

