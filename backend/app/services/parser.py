import io
import re
import pandas as pd
from fastapi import HTTPException
 
from app.config import (
    ALIASES,
    EXCLUDED_CATEGORIES,
    EXCLUDED_DESCRIPTION_PATTERNS,
    REQUIRED_COLUMNS,
)
 
 
def normalize_description(description: str) -> str:
    """Приводит название merchant к единому виду."""
    if not description:
        return ""
 
    text = str(description).lower().strip()
 
    # Убираем город/регион перед merchant (например: Ekaterinburg/MAGNIT -> magnit)
    if "/" in text:
        parts = text.split("/")
        text = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
 
    # Заменяем все не-буквенно-цифровые символы на пробелы
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
 
    # Убираем лишние пробелы
    return re.sub(r"\s+", " ", text).strip()
 
 
def display_service_name(normalized_name: str) -> str:
    """Возвращает красивое название сервиса из словаря алиасов."""
    if normalized_name in ALIASES:
        return ALIASES[normalized_name]
 
    # Если алиаса нет, просто капитализируем каждое слово
    return " ".join(word.capitalize() for word in normalized_name.split())
 
 
def parse_csv(content: bytes) -> pd.DataFrame:
    """Парсит CSV-файл с банковской выпиской с автодетекцией разделителя."""
    text = None
    for encoding in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
 
    if text is None:
        raise HTTPException(status_code=400, detail="Не удалось определить кодировку CSV")
 
    try:
        # Автодетекция разделителя: pandas сам определит ',' или ';'
        df = pd.read_csv(
            io.StringIO(text),
            sep=None,
            engine="python",
            skipinitialspace=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения CSV: {exc}")
 
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Отсутствуют обязательные колонки: {sorted(missing)}")
 
    return df
 
 
def parse_pdf(content: bytes) -> pd.DataFrame:
    """Парсит PDF-выписку (базовая поддержка табличных PDF через pdfplumber)."""
    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(status_code=500, detail="Библиотека pdfplumber не установлена")
 
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            tables = []
            for page in pdf.pages:
                table = page.extract_table()
                if table and len(table) > 1:
                    df_page = pd.DataFrame(table[1:], columns=table[0])
                    tables.append(df_page)
 
            if not tables:
                raise HTTPException(status_code=400, detail="Таблицы в PDF не найдены")
 
            df = pd.concat(tables, ignore_index=True)
            df.columns = [str(c).strip().lower() for c in df.columns]
 
            # Маппинг частых названий колонок из PDF-выписок российских банков
            mapping = {
                "дата": "operationDate", "дата операции": "operationDate",
                "мерчант": "merchant", "торговец": "merchant", "назначение": "merchant",
                "сумма": "amount", "тип": "type", "тип операции": "type",
                "категория": "category", "mcc": "mcc",
            }
            df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
 
            missing = REQUIRED_COLUMNS - set(df.columns)
            if missing:
                raise HTTPException(status_code=400, detail=f"В PDF не найдены колонки: {sorted(missing)}")
            return df
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения PDF: {exc}")
 
 
def prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает и очищает транзакции для анализа.
 
    ВАЖНО: здесь НЕ исключаются бытовые категории (Продукты, Переводы, Наличные и т.д.) —
    только техническая очистка (даты, суммы, дубликаты, нереалистичные значения).
    Это нужно, чтобы total_spent и разбивка по категориям в scan.py считались по
    ВСЕМ реальным списаниям, а не только по той узкой выборке, что уходит в ИИ-кластеризацию.
    Сужение выборки для поиска подписок делает отдельная функция exclude_for_subscription_search().
    """
    df = df.copy()
 
    # 1. Оставляем только списания
    df = df[df["type"].astype(str).str.strip().eq("Списание")]
 
    # 2. Оставляем только выполненные операции
    if "status" in df.columns:
        df = df[df["status"].fillna("").astype(str).str.strip().eq("Выполнен")]
 
    # 3. Парсим дату (день сначала)
    df["date"] = pd.to_datetime(
        df["operationDate"],
        dayfirst=True,
        errors="coerce",
        format="mixed",
    )
 
    # 4. Парсим сумму
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
 
    # 5. Обрабатываем название мерчанта
    df["raw_description"] = df["merchant"].fillna("").astype(str).str.strip()
    df["normalized"] = df["raw_description"].apply(normalize_description)
 
    # 6. Применяем алиасы для группировки
    df["service_name"] = df["normalized"].apply(display_service_name)
 
    # 7. Обрабатываем категорию и MCC
    df["category_clean"] = df["category"].fillna("").astype(str).str.strip() if "category" in df.columns else ""
    df["mcc_clean"] = pd.to_numeric(df["mcc"], errors="coerce") if "mcc" in df.columns else None
 
    # 8. Базовая очистка мусора
    df = df.dropna(subset=["date", "amount"])
    df = df[df["normalized"] != ""]
 
    # 9. Фильтр нереалистичных сумм (от 1 до 100 000 руб)
    df = df[(df["amount"] >= 1) & (df["amount"] <= 100000)]
 
    # 10. Убираем транзакции из будущего
    df = df[df["date"] <= pd.Timestamp.now().normalize()]
 
    # 11. Убираем полные дубликаты
    df = df.drop_duplicates(subset=["date", "amount", "normalized"])
 
    return df.sort_values("date")
 
 
def exclude_for_subscription_search(df: pd.DataFrame) -> pd.DataFrame:
    """
    Сужает набор транзакций ТОЛЬКО для передачи в ИИ-кластеризацию (app.services.ai):
    убирает бытовые категории и явные переводы/снятия наличных, чтобы GigaChat не тратил
    "внимание" на них при поиске подписок. На total_spent и разбивку по категориям
    в scan.py эта функция не влияет — они считаются по полному набору из prepare_transactions().
    """
    df = df[~df["category_clean"].apply(lambda x: x in EXCLUDED_CATEGORIES)]
    df = df[~df["raw_description"].apply(
        lambda x: any(p in str(x).lower() for p in EXCLUDED_DESCRIPTION_PATTERNS)
    )]
    return df
 
 
def filter_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Фильтрует транзакции по выбранному временному промежутку."""
    if df.empty or period == "all":
        return df
 
    now = pd.Timestamp.now().normalize()
 
    if period == "1m":
        start_date = now - pd.DateOffset(months=1)
    elif period == "3m":
        start_date = now - pd.DateOffset(months=3)
    elif period == "6m":
        start_date = now - pd.DateOffset(months=6)
    elif period == "1y":
        start_date = now - pd.DateOffset(years=1)
    elif period == "ytd":
        start_date = pd.Timestamp(now.year, 1, 1)
    else:
        return df
 
    return df[df["date"] >= start_date]