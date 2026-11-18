from fastapi import APIRouter, Depends

from backend.app.api.dependencies import intelligence
from backend.app.schemas import PredictionRequest, PredictionResult

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResult)
def predict(body: PredictionRequest, service=Depends(intelligence)):
    return service.predict(body)
