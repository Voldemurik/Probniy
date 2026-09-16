import os

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import MAX_FILE_SIZE
from app.models import (
    AnalyzeResponse,
    ExpenseCategory,
    PeriodType,
    SpendingOverview,
)
from app.services.ai import classify_all_expenses
from app.services.llm import get_llm_client
from app.services.parser import filter_by_period, parse_csv, parse_pdf, prepare_transactions

load_dotenv()

router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.get("/health")
def health(deep: bool = False):
    llm = get_llm_client()
    info = llm.health()
    payload = {
        "status": "ok",
        "version": "1.7.0",
        "llm": info,
    }
    if deep:
        # 06.09: самодиагностика — список моделей, пробный запрос к LLM и к эмбеддингам, текст ошибки без ключа
        if llm.provider == "gigachat":
            try:
                payload["models_available"] = llm.available_models()
                payload["llm"]["model_in_use"] = llm.resolve_model()
            except Exception as exc:
                payload["models_available"] = {"error": llm.redact(f"{type(exc).__name__}: {exc}")[:300]}
        try:
            reply = llm.chat_text([{"role": "user", "content": "Ответь одним словом: ок"}], max_tokens=5)
            payload["llm_check"] = {"ok": True, "reply": str(reply).strip()[:40]}
        except Exception as exc:
            payload["llm_check"] = {"ok": False, "error": llm.redact(f"{type(exc).__name__}: {exc}")[:400]}
        try:
            vectors = llm.embeddings(["Яндекс Плюс"])
            payload["embeddings_check"] = {"ok": True, "dim": len(vectors[0]) if vectors else 0}
        except Exception as exc:
            payload["embeddings_check"] = {"ok": False, "error": llm.redact(f"{type(exc).__name__}: {exc}")[:400]}
    return payload


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    period: PeriodType = Form(PeriodType.SIX_MONTHS),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не указан")

    file_ext = file.filename.lower().rsplit(".", 1)[-1]
    if file_ext not in {"csv", "pdf"}:
        raise HTTPException(status_code=400, detail="Поддерживаются только CSV и PDF файлы")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс 10 МБ)")

    try:
        df = parse_pdf(content) if file_ext == "pdf" else parse_csv(content)
        df = prepare_transactions(df)
        df_filtered = filter_by_period(df, period.value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось обработать выписку: {exc}") from exc

    tx_list = df_filtered[["date", "merchant", "amount", "category", "mcc"]].to_dict("records")
    clusters, subscriptions = classify_all_expenses(tx_list)

    total_spent = round(float(df_filtered["amount"].sum()), 2) if not df_filtered.empty else 0.0
    total_subscriptions = round(
        sum(c.total_amount for c in clusters if c.category == ExpenseCategory.SUBSCRIPTION), 2
    )
    total_recurring = round(
        sum(c.total_amount for c in clusters if c.category == ExpenseCategory.RECURRING_PAYMENT), 2
    )
    household_cats = {
        ExpenseCategory.HOUSEHOLD_FOOD,
        ExpenseCategory.HOUSEHOLD_TRANSPORT,
        ExpenseCategory.HOUSEHOLD_CAFE,
        ExpenseCategory.HOUSEHOLD_PHARMACY,
    }
    total_household = round(
        sum(c.total_amount for c in clusters if c.category in household_cats), 2
    )
    total_transfers_out = round(
        sum(c.total_amount for c in clusters if c.category == ExpenseCategory.TRANSFER_OUT), 2
    )

    overview = SpendingOverview(
        total_spent=total_spent,
        total_income=0.0,
        total_subscriptions=total_subscriptions,
        total_recurring=total_recurring,
        total_household=total_household,
        total_transfers_out=total_transfers_out,
        subscriptions_count=len(subscriptions),
        categories=clusters,
    )

    return AnalyzeResponse(
        subscriptions=subscriptions,
        total_monthly_savings_potential=round(sum(s.monthly_cost for s in subscriptions), 2),
        total_actual_spent=total_spent,
        period_analyzed=period.value,
        spending_overview=overview,
    )
