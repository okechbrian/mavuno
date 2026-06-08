from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class FarmerOnboardRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[0-9\s\-]{7,20}$")
    district: str = Field(..., min_length=2, max_length=50)
    acres: float = Field(..., gt=0, le=10000)
    crop: str = Field(..., min_length=2, max_length=50)

class BuyerOnboardRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    contact: str = Field(..., pattern=r"^\+?[0-9\s\-]{7,20}$")
    region: str = Field(..., min_length=2, max_length=50)
    floor_ugx: int = Field(..., gt=0)
    crops: str = Field(..., description="Comma separated list of crops")

class TelemetryRecord(BaseModel):
    farm_id: str = Field(..., max_length=64)
    soil_moisture: float = Field(..., ge=0, le=100)
    temp_c: float = Field(..., ge=-10, le=60)
    rainfall_mm: float = Field(..., ge=0, le=500)
    humidity_pct: float = Field(..., ge=0, le=100)
    n_mg_kg: float = Field(..., ge=0, le=1000)
    p_mg_kg: float = Field(..., ge=0, le=1000)
    k_mg_kg: float = Field(..., ge=0, le=2000)

class PriorityApproveRequest(BaseModel):
    farm_id: str = Field(..., max_length=64)

class CRPAskRequest(BaseModel):
    farm_id: str = Field(..., max_length=64)
    question: str = Field(..., min_length=1, max_length=500)
    make_public: bool = Field(default=False)

class PaymentBatchRequest(BaseModel):
    offer_ids: List[str]
    msisdn: str = Field(..., pattern=r"^\+?[0-9\s\-]{7,20}$")

class TrainingCompleteRequest(BaseModel):
    module_id: str = Field(..., max_length=64)

class ChatThreadReq(BaseModel):
    farm_id: str = Field(..., max_length=64)
    offer_id: Optional[str] = Field(default=None, max_length=64)

class ChatMessageReq(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)

class LogisticsOptimizeRequest(BaseModel):
    max_dist_km: float = Field(15.0, gt=0, le=500)

class LogisticsAdviseRequest(BaseModel):
    pending: List[dict]

class DemoCycleRequest(BaseModel):
    farm_id: str = Field(..., max_length=64)

class FarmStageUpdate(BaseModel):
    current_stage: str = Field(..., description="E.g., Land Prep, Vegetative, Flowering, Harvesting")

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
