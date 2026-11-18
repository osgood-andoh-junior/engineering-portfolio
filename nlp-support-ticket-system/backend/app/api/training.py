from fastapi import APIRouter, Depends

from backend.app.api.dependencies import intelligence, repository
from backend.app.schemas import TrainingRequest

router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/start", status_code=201)
def start(body: TrainingRequest, service=Depends(intelligence)):
    return service.train(body.model.value)


@router.get("/runs")
def runs(repo=Depends(repository)):
    return repo.training_runs()
