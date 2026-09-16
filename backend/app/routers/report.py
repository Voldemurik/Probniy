from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from typing import List, Optional
 
from app.models import Subscription
from app.services.ai import generate_recommendations
 
router = APIRouter(prefix="/api/v1", tags=["report"])
 
 
class ReportRequest(BaseModel):
    subscriptions: List[dict]
    total_spent: float
    total_income: float
    period: Optional[str] = None            # 06.09: период анализа ('1m', '3m', '6m', '1y', 'ytd', 'all')
 
 
_PERIOD_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "ytd": None, "all": None}
 
 
@router.post("/report")
async def generate_report_endpoint(request: ReportRequest) -> str:
    """Генерирует рекомендации по подпискам, используя единую логику из ai.py."""
    try:
        subs_objects = [Subscription(**s) for s in request.subscriptions]
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Некорректный формат подписок: {exc}")
 
    return generate_recommendations(
        subscriptions=subs_objects,
        total_spent=request.total_spent,
        total_income=request.total_income,
        period_months=_PERIOD_MONTHS.get(request.period or "", None),
    )
 