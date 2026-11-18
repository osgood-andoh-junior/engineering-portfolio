from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Category = Literal["Network", "Account", "Payment", "Software", "Hardware", "Other"]
TicketText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]


class ModelName(str, Enum):
    NAIVE_BAYES = "naive_bayes"
    NEURAL_NETWORK = "neural_network"
    RNN = "rnn"
    ATTENTION = "attention"
    TRANSFORMER = "transformer"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TicketCreate(StrictModel):
    text: TicketText
    actual_category: Category | None = None


class TicketUpdate(StrictModel):
    text: TicketText | None = None
    actual_category: Category | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field.")
        if "text" in self.model_fields_set and self.text is None:
            raise ValueError("text cannot be null.")
        return self


class Ticket(TicketCreate):
    id: int
    predicted_category: Category | None
    confidence: float | None
    model_version: str | None
    created_at: str


class PredictionRequest(StrictModel):
    text: TicketText | None = None
    ticket_id: int | None = Field(default=None, gt=0)
    model_version: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def one_source(self):
        if (self.text is None) == (self.ticket_id is None):
            raise ValueError("Provide exactly one of text or ticket_id.")
        return self


class PredictionResult(StrictModel):
    category: Category
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    model: str
    processing_time_ms: float = Field(ge=0)


class TrainingRequest(StrictModel):
    model: ModelName = ModelName.NAIVE_BAYES


class Metrics(StrictModel):
    accuracy: float = Field(ge=0, le=1, allow_inf_nan=False)
    precision: float = Field(ge=0, le=1, allow_inf_nan=False)
    recall: float = Field(ge=0, le=1, allow_inf_nan=False)
    f1: float = Field(ge=0, le=1, allow_inf_nan=False)
