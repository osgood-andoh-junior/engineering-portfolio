from fastapi import APIRouter, Depends

from backend.app.api.dependencies import repository

router = APIRouter(tags=["registry"])


@router.get("/api/models")
def models(repo=Depends(repository)):
    return repo.models()


@router.get("/api/evaluations")
def evaluations(repo=Depends(repository)):
    return repo.evaluations()
