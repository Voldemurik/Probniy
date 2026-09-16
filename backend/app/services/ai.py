"""AI-классификация расходов через единый LLM-адаптер.

Провайдер выбирается только через LLM_PROVIDER/LLM_API_KEY/LLM_BASE_URL/LLM_MODEL.
Никакого отдельного GIGACHAT_AUTH_KEY здесь нет.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from app.config import ALIASES, KNOWN_NON_SUBSCRIPTION_SERVICES, KNOWN_SUBSCRIPTION_SERVICES, SUBSCRIPTION_CATEGORY_RU
from app.models import ExpenseCategory, ExpenseCluster, Subscription, Transaction
from app.services.detector import detect_alerts, detect_frequency
from app.services.llm import LLMError, get_llm_client
from app.services.naming import canonical_name, merge_clusters_by_embeddings


class AIClusterResponse(BaseModel):
    id: Optional[int] = None
    category: str = "other"
    canonical_name: str = ""
    total_amount: float = 0.0
    transaction_count: int = 0
    is_subscription: bool = False
    mir_compatible: bool = True
    cancellation_guide: Optional[str] = None
    confidence: str = "medium"
    reason: str = ""


class AIResponse(BaseModel):
    clusters: List[AIClusterResponse]


SYSTEM_PROMPT = """
Ты — финансовый AI-аналитик российского банка.
Классифицируй каждый кластер транзакций строго в одну категорию.

Категории:
- subscription: цифровая подписка с автопродлением;
- recurring_payment: регулярный платёж, но не цифровая подписка (рассрочки, обучение, ЖКХ и т.п.);
- transfer_out: перевод/вывод денег;
- transfer_in: поступление;
- household_food: продукты;
- household_transport: транспорт;
- household_cafe: кафе/рестораны;
- household_pharmacy: аптеки;
- marketplace: маркетплейсы;
- cash_withdrawal: наличные;
- entertainment: разовые развлечения;
- other: всё остальное.

Правила:
1. Skillbox, GeekBrains, Нетология, SkillFactory и Учи.ру — recurring_payment, НЕ subscription.
2. Если сервис не принимает МИР, mir_compatible=false и is_subscription=false.
3. Российские цифровые сервисы могут быть subscription, но только при явной регулярности.
4. Разовые покупки нельзя объявлять подписками только по названию мерчанта.
5. Если данных недостаточно, confidence=low и is_subscription=false.
6. Для subscription дай cancellation_guide.
7. Связь и домашний интернет с фиксированной абонентской платой (Ростелеком, МТС, Билайн и т.п.)
   при стабильной сумме и регулярности — subscription.
8. Верни только валидный JSON вида {"clusters": [...]}.
""".strip()


def _normalize_merchant(raw: str) -> str:
    if not raw:
        return ""
    text = str(raw).lower().strip()
    # Не уничтожаем URL-подобные названия: алиасы config.py уже содержат нормальные формы.
    text = text.replace("/", " ")
    text = re.sub(r"[^\w\s.+-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _canonical_name(raw: str) -> str:
    # 06.09: нормализация и словарь алиасов вынесены в services/naming.py —
    # так «YANDEX.PLUS», «Yandex Plus» и «ЯНДЕКС ПЛЮС» попадают в один кластер.
    return canonical_name(raw) or _normalize_merchant(raw).title()


def _merge_variants_with_embeddings(clusters_data: List[Dict]) -> List[Dict]:
    """Шаг 2 кластеризации: эмбеддинги GigaChat для названий, которых нет в словаре.
    Выключается переменной LLM_EMBEDDINGS=0. Любая ошибка → возвращаем кластеры как есть."""
    if os.getenv("LLM_EMBEDDINGS", "1").strip().lower() in {"0", "false", "no", "off"}:
        return clusters_data
    client = get_llm_client()
    if client.provider != "gigachat" or not client.is_configured():
        return clusters_data
    try:
        merged = merge_clusters_by_embeddings(clusters_data, client.embeddings)
        if len(merged) < len(clusters_data):
            print(f"🔗 Эмбеддинги GigaChat: {len(clusters_data)} → {len(merged)} кластеров")
        return merged
    except Exception as exc:
        print(f"⚠️ Эмбеддинги недоступны, кластеризация только по словарю: {exc}")
        return clusters_data


def _simple_cluster(transactions: List[Dict]) -> List[Dict]:
    clusters: Dict[str, Dict] = {}
    for tx in transactions:
        merchant = str(tx.get("merchant", "")).strip()
        if not merchant:
            continue
        canonical = _canonical_name(merchant)
        if not canonical:
            continue
        item = clusters.setdefault(
            canonical,
            {
                "canonical_name": canonical,
                "merchant_variations": set(),
                "transactions": [],
                "category_hint": str(tx.get("category", "") or ""),
                "mcc": tx.get("mcc"),
            },
        )
        item["merchant_variations"].add(merchant)
        item["transactions"].append(tx)

    result = []
    for item in clusters.values():
        txs = item["transactions"]
        result.append(
            {
                "canonical_name": item["canonical_name"],
                "merchant_variations": sorted(item["merchant_variations"]),
                "transactions": txs,
                "total_amount": round(sum(float(t.get("amount", 0)) for t in txs), 2),
                "count": len(txs),
                "category_hint": item["category_hint"],
                "mcc": item["mcc"],
            }
        )
    return result


def _compact_clusters(clusters_data: List[Dict]) -> List[Dict]:
    return [
        {
            "id": i,
            "canonical_name": c["canonical_name"],
            "merchants": c["merchant_variations"][:8],
            "amounts": [round(float(t.get("amount", 0)), 2) for t in c["transactions"][:12]],
            "dates": [_format_date(t.get("date")) for t in c["transactions"][:12]],
            "count": c["count"],
            "total": c["total_amount"],
            "bank_category": c["category_hint"],
            "mcc": c.get("mcc"),
        }
        for i, c in enumerate(clusters_data)
    ]


def _extract_json(raw: str) -> Dict:
    """Достаёт JSON-объект из ответа модели: убирает ```-обрамление, берёт от первой { до последней }."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    obj_start, arr_start = text.find("{"), text.find("[")
    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        start, end = arr_start, text.rfind("]")      # модель вернула список кластеров без обёртки
    else:
        start, end = obj_start, text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("В ответе модели нет JSON", text[:80], 0)
    data = json.loads(text[start:end + 1])
    if isinstance(data, list):
        data = {"clusters": data}
    return data


def _merge_llm_with_clusters(items: List[AIClusterResponse], clusters_data: List[Dict]) -> List[AIClusterResponse]:
    """Сопоставляет ответы модели с нашими кластерами (по id, иначе по имени), суммы и число
    транзакций берёт из наших данных, а кластеры, которые модель пропустила, классифицирует правилами."""
    by_id: Dict[int, AIClusterResponse] = {}
    by_name: Dict[str, AIClusterResponse] = {}
    for item in items:
        if item.id is not None:
            by_id.setdefault(int(item.id), item)
        if item.canonical_name:
            by_name.setdefault(item.canonical_name.strip().lower(), item)

    result: List[AIClusterResponse] = []
    missing = 0
    for i, c in enumerate(clusters_data):
        item = by_id.get(i) or by_name.get(c["canonical_name"].strip().lower())
        if item is None:
            missing += 1
            item = _heuristic_fallback([c])[0]
        else:
            item = item.model_copy(update={
                "id": i,
                "canonical_name": c["canonical_name"],
                "total_amount": c["total_amount"],
                "transaction_count": c["count"],
            })
        result.append(item)
    if missing:
        print(f"ℹ️ Модель пропустила {missing} кластеров — дозаполнены правилами")
    return result


def _call_llm(clusters_data: List[Dict]) -> List[AIClusterResponse]:
    client = get_llm_client()
    if not client.is_configured():
        print(f"⚠️ LLM не настроен: provider={client.provider}; используется эвристический fallback")
        return []

    prompt = (
        "Проанализируй кластеры транзакций. Не придумывай транзакции и не меняй суммы. "
        "Для каждого id верни ровно один объект с полями id, category, canonical_name, "
        "is_subscription, mir_compatible, cancellation_guide, confidence, reason.\n\n"
        + json.dumps(_compact_clusters(clusters_data), ensure_ascii=False, indent=2)
    )

    try:
        raw = client.chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        parsed = AIResponse.model_validate(_extract_json(raw))
        if not parsed.clusters:
            print("⚠️ LLM вернул пустой список кластеров")
            return []
        print(f"✅ LLM ({client.provider}, {client.model_in_use}) вернул {len(parsed.clusters)} кластеров")
        return _merge_llm_with_clusters(parsed.clusters, clusters_data)
    except (json.JSONDecodeError, ValidationError) as exc:
        print(f"⚠️ LLM вернул невалидный JSON: {str(exc)[:200]}")
    except LLMError as exc:
        print(f"⚠️ Ошибка LLM: {exc}")
    except Exception as exc:
        print(f"⚠️ Неожиданная ошибка LLM: {exc}")
    return []


def _heuristic_classify(merchants: str, bank_cat: str, mcc, canonical: str = "") -> Tuple[str, bool, bool]:
    lower = merchants.lower()
    if any(k in lower for k in ("снятие", "atm", "банкомат", "cash withdrawal")):
        return "cash_withdrawal", False, True
    if bank_cat == "Переводы":
        return "transfer_out", False, True

    # 06.09: сначала словарь известных сервисов по каноническому имени (после алиасов)
    if canonical in KNOWN_NON_SUBSCRIPTION_SERVICES:
        return "recurring_payment", False, True
    if canonical in KNOWN_SUBSCRIPTION_SERVICES:
        foreign_known = {"Netflix", "Spotify", "Apple Music", "YouTube Premium", "YouTube Music", "ChatGPT", "OpenAI"}
        return ("subscription", canonical not in foreign_known, canonical not in foreign_known)
    # такси, еда, маркет, лавка — покупки, а не подписки, даже если бренд «подписочный»
    if any(k in lower for k in ("taxi", "такси", "eda", "еда", "market", "маркет", "lavka", "лавка", " go", "delivery", "доставка")):
        return "other", False, True

    non_sub = ("skillbox", "geekbrains", "нетология", "skillfactory", "учи.ру", "uchi")
    if any(k in lower for k in non_sub):
        return "recurring_payment", False, True

    foreign = ("spotify", "netflix", "patreon", "apple music")
    if any(k in lower for k in foreign):
        return "other", False, False

    subscription_keywords = (
        "yandex", "яндекс", "sberprime", "сберпрайм", "zvuk", "sberzvuk", "ivi",
        "окко", "okko", "kinopoisk", "кинопоиск", "premier", "start", "fitmost",
        "фитмост", "vk music", "вк музыка", "vkplay", "vk play", "lesta", "litres",
        "литрес", "cloud mail", "vk cloud", "icloud", "chatgpt", "openai",
    )
    if any(k in lower for k in subscription_keywords):
        return "subscription", True, True

    cat_map = {
        "Продукты": "household_food",
        "Транспорт": "household_transport",
        "Кафе": "household_cafe",
        "Фастфуд": "household_cafe",
        "Аптеки": "household_pharmacy",
        "Маркетплейсы": "marketplace",
        "Наличные": "cash_withdrawal",
    }
    if bank_cat in cat_map:
        return cat_map[bank_cat], False, True

    try:
        mcc_int = int(float(mcc)) if mcc is not None and str(mcc).strip() else None
    except (TypeError, ValueError):
        mcc_int = None
    mcc_map = {
        5411: "household_food", 5499: "household_food", 4111: "household_transport",
        4131: "household_transport", 5812: "household_cafe", 5814: "household_cafe",
        5912: "household_pharmacy", 5300: "marketplace", 6011: "cash_withdrawal",
        5815: "entertainment", 5816: "entertainment", 5817: "entertainment", 5818: "entertainment",
    }
    return mcc_map.get(mcc_int, "other"), False, True


def _heuristic_fallback(clusters_data: List[Dict]) -> List[AIClusterResponse]:
    result = []
    for c in clusters_data:
        merchants = " ".join(c["merchant_variations"])
        category, is_sub, mir = _heuristic_classify(merchants, c["category_hint"], c.get("mcc"), c.get("canonical_name", ""))
        result.append(
            AIClusterResponse(
                category=category,
                canonical_name=c["canonical_name"],
                total_amount=c["total_amount"],
                transaction_count=c["count"],
                is_subscription=is_sub,
                mir_compatible=mir,
                confidence="low",
                reason="Эвристическая классификация (LLM недоступен)",
            )
        )
    return result


def _format_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def _find_cluster_transactions(clusters_data: List[Dict], canonical_name: str) -> List[Dict]:
    target = canonical_name.strip().lower()
    for cluster in clusters_data:
        if cluster["canonical_name"].strip().lower() == target:
            return cluster["transactions"]
    return []


_CHARGES_PER_YEAR = {"weekly": 52, "biweekly": 26, "monthly": 12, "quarterly": 4, "yearly": 1}
_NEXT_OFFSET = {
    "weekly": pd.DateOffset(weeks=1),
    "biweekly": pd.DateOffset(weeks=2),
    "monthly": pd.DateOffset(months=1),
    "quarterly": pd.DateOffset(months=3),
    "yearly": pd.DateOffset(years=1),
}


def _build_subscription(ai: AIClusterResponse, txs: List[Dict]) -> Optional[Subscription]:
    if not txs:
        return None
    amounts = [float(t.get("amount", 0)) for t in txs]
    total_spent = round(sum(amounts), 2)
    raw_dates = [t.get("date") for t in txs if t.get("date") is not None]
    parsed_dates = [d for d in (pd.to_datetime(x, errors="coerce") for x in raw_dates) if pd.notna(d)]
    frequency = detect_frequency(parsed_dates) or "monthly"

    # 06.09: цена = последнее по дате списание; месячная стоимость приводится к частоте
    dated = sorted(
        ((pd.to_datetime(t.get("date"), errors="coerce"), float(t.get("amount", 0))) for t in txs),
        key=lambda pair: (pd.Timestamp.min if pd.isna(pair[0]) else pair[0]),
    )
    charge_amount = round(dated[-1][1] if dated else amounts[-1], 2)
    per_year = _CHARGES_PER_YEAR.get(frequency, 12)
    yearly_savings = round(charge_amount * per_year, 2)
    monthly_cost = round(yearly_savings / 12, 2)
    last_dt = max(parsed_dates) if parsed_dates else None
    last_charge = last_dt.strftime("%Y-%m-%d") if last_dt is not None else None
    next_charge = (
        (last_dt + _NEXT_OFFSET.get(frequency, pd.DateOffset(months=1))).strftime("%Y-%m-%d")
        if last_dt is not None else None
    )

    tx_df = pd.DataFrame({"date": parsed_dates, "amount": amounts}) if parsed_dates else pd.DataFrame()
    alerts = detect_alerts(tx_df) if not tx_df.empty else []
    if ai.reason:
        alerts.append(f"AI-анализ: {ai.reason}")
    if ai.cancellation_guide:
        alerts.append(f"Инструкция по отписке: {ai.cancellation_guide}")

    return Subscription(
        service_name=ai.canonical_name,
        monthly_cost=monthly_cost,
        yearly_cost=round(monthly_cost * 12, 2),
        frequency=frequency,
        confidence=ai.confidence,
        alerts=alerts,
        transactions=[
            Transaction(
                date=_format_date(t.get("date")),
                amount=round(float(t.get("amount", 0)), 2),
                raw_description=str(t.get("merchant", "")),
                category=str(t.get("category", "")),
            )
            for t in txs
        ],
        subscription_type="subscription",
        actual_spent_in_period=total_spent,
        mir_compatible=ai.mir_compatible,
        cancellation_guide=ai.cancellation_guide,
        charge_amount=charge_amount,
        charges_count=len(txs),
        last_charge=last_charge,
        next_charge=next_charge,
        yearly_savings=yearly_savings,
    )


def classify_all_expenses(transactions: List[Dict]) -> Tuple[List[ExpenseCluster], List[Subscription]]:
    if not transactions:
        return [], []

    clusters_data = _simple_cluster(transactions)
    if not clusters_data:
        return [], []
    clusters_data = _merge_variants_with_embeddings(clusters_data)

    ai_clusters = _call_llm(clusters_data)
    if not ai_clusters:
        print("⚠️ Используем эвристический fallback")
        ai_clusters = _heuristic_fallback(clusters_data)

    expense_clusters: List[ExpenseCluster] = []
    subscriptions: List[Subscription] = []
    valid_categories = {e.value for e in ExpenseCategory}

    for ai in ai_clusters:
        txs = _find_cluster_transactions(clusters_data, ai.canonical_name)
        category = ExpenseCategory(ai.category) if ai.category in valid_categories else ExpenseCategory.OTHER
        expense_clusters.append(
            ExpenseCluster(
                category=category,
                canonical_name=ai.canonical_name,
                total_amount=ai.total_amount,
                transaction_count=ai.transaction_count,
                transactions=[
                    Transaction(
                        date=_format_date(t.get("date")),
                        amount=float(t.get("amount", 0)),
                        raw_description=str(t.get("merchant", "")),
                        category=str(t.get("category", "")),
                    )
                    for t in txs
                ],
                is_subscription=ai.is_subscription,
                mir_compatible=ai.mir_compatible,
                cancellation_guide=ai.cancellation_guide,
                confidence=ai.confidence,
                reason=ai.reason,
            )
        )
        if ai.is_subscription and ai.mir_compatible:
            sub = _build_subscription(ai, txs)
            if sub:
                subscriptions.append(sub)

    subscriptions.sort(key=lambda x: x.actual_spent_in_period, reverse=True)
    return expense_clusters, subscriptions


_PERIOD_RU = {"weekly": "неделю", "biweekly": "две недели", "monthly": "месяц", "quarterly": "квартал", "yearly": "год"}
_FREQ_EVERY_RU = {"weekly": "каждую неделю", "biweekly": "раз в две недели", "monthly": "каждый месяц",
                  "quarterly": "раз в квартал", "yearly": "раз в год"}


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _fmt_rub(value: float) -> str:
    return f"{int(round(value or 0)):,}".replace(",", " ") + " ₽"


def _period_label(period_months: Optional[float]) -> str:
    if not period_months:
        return "за период выписки"
    m = int(round(period_months))
    if m == 1:
        return "за месяц"
    if m in (2, 3, 4):
        return f"за {m} месяца"
    if m == 12:
        return "за год"
    return f"за {m} месяцев"


def _subscription_facts(subscriptions: List[Subscription], period_months: Optional[float]) -> str:
    """Компактная таблица фактов о подписках для промпта — только то, что реально посчитано."""
    lines = []
    for s in subscriptions:
        price = s.charge_amount if s.charge_amount is not None else s.monthly_cost
        lines.append(
            f"- {s.service_name}: {_fmt_rub(price)} {_FREQ_EVERY_RU.get(s.frequency, 'каждый месяц')}; "
            f"списаний за период: {s.charges_count or len(s.transactions)}; "
            f"потрачено {_period_label(period_months)}: {_fmt_rub(s.actual_spent_in_period)}; "
            f"последнее списание: {s.last_charge or '—'}; "
            f"экономия за год при отказе: {_fmt_rub(s.yearly_savings if s.yearly_savings is not None else s.yearly_cost)}"
            + (f"; заметки: {'; '.join(a for a in s.alerts if not a.startswith('AI-анализ') and not a.startswith('Инструкция'))}"
               if any(not a.startswith('AI-анализ') and not a.startswith('Инструкция') for a in s.alerts) else "")
        )
    return "\n".join(lines) or "Подписок не найдено."


RECOMMENDATIONS_SYSTEM_PROMPT = """
Ты — дружелюбный финансовый ассистент банка. Пользователь загрузил выписку, сервис уже нашёл подписки.
Напиши 3–5 рекомендаций ТОЛЬКО о подписках из списка ниже. Про продукты, переводы, кафе и другие
расходы не пиши вообще.

Требования:
- Смешай общие советы (например: «Изучите проведённый мной анализ: всеми ли сервисами вы пользуетесь
  по настоящее время?») и конкретные — с названием подписки и суммой из списка (например:
  «За 6 месяцев вы потратили 5 994 ₽ на VK Play. Играете ли вы на постоянной основе? Возможно, стоит
  отказаться от этой траты»).
- Конкретных советов должно быть больше, чем общих; начни с самой дорогой по сумме за период подписки.
- Если есть сервисы одной категории (несколько видеосервисов, несколько облаков) — предложи оставить один.
- Используй только суммы и факты из списка, ничего не придумывай и не добавляй подписки, которых нет.
- Обращайся на «вы». Формат: нумерованный список, каждый пункт 1–2 предложения, простой текст без markdown,
  без заголовков и вступлений.
""".strip()


def _heuristic_recommendations(subscriptions: List[Subscription], period_months: Optional[float]) -> str:
    """Рекомендации без LLM: строятся из тех же фактов (самые дорогие, дубли категорий, заметки)."""
    period = _period_label(period_months)
    if not subscriptions:
        return (
            "1. В выписке за выбранный период не найдено активных подписок — регулярных списаний "
            "одного сервиса с автопродлением.\n"
            "2. Если подписки есть, но оплачиваются другой картой, загрузите выписку по ней.\n"
            "3. Проверьте пробные периоды: они превращаются в платные незаметно."
        )

    items: List[str] = []
    ordered = sorted(subscriptions, key=lambda s: s.actual_spent_in_period, reverse=True)
    top = ordered[0]
    items.append(
        f"Больше всего {period} ушло на «{top.service_name}» — {_fmt_rub(top.actual_spent_in_period)} "
        f"({_fmt_rub(top.charge_amount or top.monthly_cost)} {_FREQ_EVERY_RU.get(top.frequency, 'каждый месяц')}). "
        f"Пользуетесь ли вы этим сервисом регулярно? Если нет, отказ сэкономит "
        f"{_fmt_rub(top.yearly_savings if top.yearly_savings is not None else top.yearly_cost)} в год."
    )
    if len(ordered) > 1:
        second = ordered[1]
        items.append(
            f"«{second.service_name}» списывает {_fmt_rub(second.charge_amount or second.monthly_cost)} "
            f"{_FREQ_EVERY_RU.get(second.frequency, 'каждый месяц')}, {period} — {_fmt_rub(second.actual_spent_in_period)}. "
            f"Убедитесь, что не платите за то же самое в другом сервисе."
        )

    by_category: Dict[str, List[Subscription]] = {}
    for s in subscriptions:
        for cat, names in SUBSCRIPTION_CATEGORY_RU.items():
            if s.service_name in names:
                by_category.setdefault(cat, []).append(s)
    for cat, subs in by_category.items():
        if len(subs) >= 2 and len(items) < 4:
            total_year = sum((s.yearly_savings if s.yearly_savings is not None else s.yearly_cost) for s in subs)
            names = ", ".join(s.service_name for s in subs)
            items.append(
                f"У вас {len(subs)} {_plural(len(subs), 'сервис', 'сервиса', 'сервисов')} категории «{cat}»: {names}. Обычно достаточно одного — "
                f"вместе они стоят {_fmt_rub(total_year)} в год."
            )

    for s in subscriptions:
        notes = [a for a in s.alerts if a.startswith("Обнаружено повышение") or a.startswith("Возможно, закончился")]
        if notes and len(items) < 4:
            items.append(f"«{s.service_name}»: {notes[0].lower()}. Проверьте, устраивает ли вас текущая цена.")
            break

    items.append(
        "Изучите проведённый мной анализ: всеми ли сервисами вы пользуетесь по настоящее время? "
        "Даты следующих списаний указаны выше — отменить подписку выгоднее до них."
    )
    total_year = sum((s.yearly_savings if s.yearly_savings is not None else s.yearly_cost) for s in subscriptions)
    if len(items) < 5:
        items.append(
            f"Если отказаться от всех найденных подписок, за год останется {_fmt_rub(total_year)}. "
            f"Начните с тех, которыми не пользовались последний месяц."
        )
    return "\n".join(f"{i + 1}. {text}" for i, text in enumerate(items[:5]))


def generate_recommendations(
    subscriptions: List[Subscription],
    total_spent: float,
    total_income: float,
    clusters: Optional[List[ExpenseCluster]] = None,
    period_months: Optional[float] = None,
) -> str:
    """Рекомендации только по подпискам: GigaChat по фактам из анализа, при недоступности — эвристика."""
    client = get_llm_client()
    if client.is_configured():
        facts = _subscription_facts(subscriptions, period_months)
        total_year = sum((s.yearly_savings if s.yearly_savings is not None else s.yearly_cost) for s in subscriptions)
        prompt = (
            f"Период выписки: {_period_label(period_months)}. Всего потрачено за период (все расходы): "
            f"{_fmt_rub(total_spent)}; на подписки: {_fmt_rub(sum(s.actual_spent_in_period for s in subscriptions))}; "
            f"если отказаться от всех подписок — {_fmt_rub(total_year)} в год.\n\n"
            f"Найденные подписки:\n{facts}\n\nНапиши рекомендации."
        )
        try:
            text = client.chat_text(
                [
                    {"role": "system", "content": RECOMMENDATIONS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            text = (text or "").strip()
            if text:
                return text
        except LLMError as exc:
            print(f"⚠️ Ошибка рекомендаций LLM: {exc}")
        except Exception as exc:
            print(f"⚠️ Неожиданная ошибка рекомендаций LLM: {exc}")

    return _heuristic_recommendations(subscriptions, period_months)
